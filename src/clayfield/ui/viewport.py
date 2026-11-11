"""Shader-backed OpenGL viewport for the foundation milestone."""

from __future__ import annotations

import ctypes
import math
from array import array
from pathlib import Path

import numpy as np
from OpenGL.GL import *
from OpenGL.raw.GL.VERSION.GL_2_0 import glVertexAttribPointer
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMatrix4x4
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from clayfield.image.curves import curve_lut
from clayfield.ui.axis_gizmo import AxisGizmo
from clayfield.ui.camera import OrbitCamera
from clayfield.ui.gpu_pipeline import GpuImagePipeline, supports_gpu_adjustments


def _block_mean(values: np.ndarray, target_rows: int, target_columns: int) -> np.ndarray:
    """Downscale a 2D array by averaging non-overlapping blocks (box filter).

    ``np.add.reduceat`` is used instead of reshape-and-mean so odd row/column
    counts and non-integer bin widths still average every source sample exactly
    once. The result is float32 and C-contiguous, which is what the texture
    upload expects.
    """
    rows, columns = values.shape
    if target_rows == rows and target_columns == columns:
        return values
    row_starts = np.linspace(0, rows, target_rows + 1, dtype=np.int64)[:-1]
    column_starts = np.linspace(0, columns, target_columns + 1, dtype=np.int64)[:-1]
    row_counts = np.diff(np.append(row_starts, rows))
    column_counts = np.diff(np.append(column_starts, columns))
    row_sums = np.add.reduceat(values, row_starts, axis=0)
    block_sums = np.add.reduceat(row_sums, column_starts, axis=1)
    means = block_sums / (row_counts[:, None] * column_counts[None, :])
    return np.ascontiguousarray(means, dtype=np.float32)


class Viewport(QOpenGLWidget):
    """Render a reference grid and provide basic camera interaction."""

    gpu_adjustments_ready = Signal(int, object)
    gpu_error = Signal(str)
    initialization_failed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.camera = OrbitCamera()
        self.program = 0
        self._gl_ready = False
        self.vao = 0
        self.vbo = 0
        self.surface_vao = 0
        self.surface_vbo = 0
        self.surface_vertex_count = 0
        self._surface_grid_key = None
        self.height_texture = 0
        self._pending_heightfield = None
        self._pending_gpu = None
        self._gpu_pipeline = None
        self._gpu_surface = None
        self._mapping_texture = 0
        self.gpu_adjustments_enabled = True
        self.vertex_count = 0
        self.last_position = None
        self._drag_button = None
        self.wireframe = False
        self.orthographic = False
        self.show_grid = True
        self.height_coloring = False
        self.height_min_mm = 0.0
        self.height_max_mm = 8.0
        self.surface_color = (0.42, 0.64, 0.82)
        self.light_azimuth = 135.0
        self._surface_extent = 5.0
        self._sample_spacing = (1.0, 1.0)
        self.renderer = "Unavailable"
        self.version = "Unavailable"
        self.shader_dir = Path(__file__).resolve().parents[1] / "resources"
        self.setMinimumSize(480, 360)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.axis_gizmo = AxisGizmo(self)
        self.axis_gizmo.set_view_matrix(self.camera.view_matrix())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.axis_gizmo.move(self.width() - self.axis_gizmo.width() - 12, 12)

    def initializeGL(self) -> None:
        self.context().aboutToBeDestroyed.connect(self._cleanup_gpu_resources)
        try:
            self._initialize_gl()
            self._gl_ready = True
        except Exception as error:
            self.initialization_failed.emit(f"OpenGL initialization failed: {error}")

    def _initialize_gl(self) -> None:
        glClearColor(0.055, 0.065, 0.08, 1.0)
        glEnable(GL_DEPTH_TEST)
        self.renderer = glGetString(GL_RENDERER).decode()
        self.version = glGetString(GL_VERSION).decode()
        self.program = self._program_from_files()
        vertices = array("f")
        extent, divisions = 2.5, 20
        step = extent * 2 / divisions
        for i in range(divisions + 1):
            c = -extent + i * step
            vertices.extend((c, 0, -extent, c, 0, extent, -extent, 0, c, extent, 0, c))
        self.vertex_count = len(vertices) // 3
        self.vao, self.vbo = glGenVertexArrays(1), glGenBuffers(1)
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.tobytes(), GL_STATIC_DRAW)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
        glEnableVertexAttribArray(0)
        glVertexAttrib3f(1, 0.0, 1.0, 0.0)
        glBindVertexArray(0)

    def paintGL(self) -> None:
        if not self._gl_ready:
            return
        self.axis_gizmo.set_view_matrix(self.camera.view_matrix())
        if self._pending_gpu is not None:
            generation, image, settings, points, terrain = self._pending_gpu
            self._pending_gpu = None
            try:
                if self._gpu_pipeline is None:
                    self._gpu_pipeline = GpuImagePipeline()
                texture = self._gpu_pipeline.process(image, settings, points, readback=False)
                self._prepare_gpu_surface(texture, image.shape, terrain)
                self.gpu_adjustments_ready.emit(generation, None)
            except Exception as error:
                self.gpu_adjustments_enabled = False
                self.gpu_error.emit(f"GPU image preview unavailable: {error}")
        if self._pending_heightfield is not None:
            heightfield, width, depth = self._pending_heightfield
            self._pending_heightfield = None
            self._upload_heightfield(heightfield, width, depth)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if self.wireframe else GL_FILL)
        if not self.program:
            return
        projection = QMatrix4x4()
        near = max(0.001, self.camera.distance / 10000.0)
        far = max(100.0, self.camera.distance + self._surface_extent * 4.0)
        aspect = self.width() / max(1, self.height())
        if self.orthographic:
            half_height = self.camera.distance * math.tan(math.radians(22.5))
            projection.ortho(-half_height * aspect, half_height * aspect, -half_height, half_height, near, far)
        else:
            projection.perspective(45, aspect, near, far)
        model = QMatrix4x4()
        glUseProgram(self.program)
        for name, matrix in (("projection", projection), ("view", self.camera.view_matrix()), ("model", model)):
            glUniformMatrix4fv(glGetUniformLocation(self.program, name), 1, GL_FALSE, matrix.data())
        glUniform1i(glGetUniformLocation(self.program, "gpu_displacement"), 0)
        glUniform1i(glGetUniformLocation(self.program, "map_gpu_intensity"), 0)
        glUniform1i(glGetUniformLocation(self.program, "lit_surface"), 0)
        glUniform1i(glGetUniformLocation(self.program, "height_coloring"), 0)
        azimuth = math.radians(self.light_azimuth)
        glUniform3f(glGetUniformLocation(self.program, "light_direction"), math.cos(azimuth), 1.0, math.sin(azimuth))
        glUniform1f(glGetUniformLocation(self.program, "ambient_strength"), 0.3)
        glUniform2f(glGetUniformLocation(self.program, "sample_spacing"), *self._sample_spacing)
        glUniform1f(glGetUniformLocation(self.program, "height_min"), self.height_min_mm / 20.0)
        glUniform1f(glGetUniformLocation(self.program, "height_max"), self.height_max_mm / 20.0)
        glUniform3f(glGetUniformLocation(self.program, "color"), 0.28, 0.62, 0.78)
        if self.show_grid:
            glBindVertexArray(self.vao)
            glDrawArrays(GL_LINES, 0, self.vertex_count)
            glBindVertexArray(0)
        if self.surface_vao and self.surface_vertex_count:
            glUniform1i(glGetUniformLocation(self.program, "gpu_displacement"), 1)
            glActiveTexture(GL_TEXTURE0)
            gpu_surface = self._gpu_surface
            glBindTexture(GL_TEXTURE_2D, gpu_surface["texture"] if gpu_surface else self.height_texture)
            glUniform1i(glGetUniformLocation(self.program, "height_texture"), 0)
            glUniform1i(glGetUniformLocation(self.program, "map_gpu_intensity"), int(gpu_surface is not None))
            if gpu_surface:
                glActiveTexture(GL_TEXTURE1)
                glBindTexture(GL_TEXTURE_2D, self._mapping_texture)
                glUniform1i(glGetUniformLocation(self.program, "mapping_curve"), 1)
                glUniform2f(
                    glGetUniformLocation(self.program, "physical_height_bounds"),
                    gpu_surface["minimum"],
                    gpu_surface["maximum"],
                )
                glUniform1f(glGetUniformLocation(self.program, "mapping_gamma"), gpu_surface["gamma"])
                glUniform1f(glGetUniformLocation(self.program, "relief_sign"), gpu_surface["sign"])
            glUniform1i(glGetUniformLocation(self.program, "lit_surface"), 1)
            glUniform1i(glGetUniformLocation(self.program, "height_coloring"), int(self.height_coloring))
            glUniform1f(glGetUniformLocation(self.program, "height_min"), self.height_min_mm / 20.0)
            glUniform1f(glGetUniformLocation(self.program, "height_max"), self.height_max_mm / 20.0)
            glUniform3f(glGetUniformLocation(self.program, "color"), *self.surface_color)
            glBindVertexArray(self.surface_vao)
            glDrawArrays(GL_TRIANGLES, 0, self.surface_vertex_count)
            glBindVertexArray(0)

    def set_height_range(self, minimum_mm: float, maximum_mm: float) -> None:
        """Set physical height bounds used by the height-coloring ramp."""
        minimum = float(minimum_mm)
        maximum = float(maximum_mm)
        if not math.isfinite(minimum) or not math.isfinite(maximum):
            raise ValueError("Height bounds must be finite")
        if maximum <= minimum:
            raise ValueError("Maximum height must exceed minimum height")
        self.height_min_mm = minimum
        self.height_max_mm = maximum
        self.update()

    def request_gpu_adjustments(self, generation: int, image, settings, points, terrain) -> None:
        """Queue a direct texture preview; unsupported modifiers use the CPU."""
        blur = float(settings.get("Blur", 0))
        radius = (max(3, int(round(blur * 6)) | 1) // 2) if blur else 0
        fetches = 1 + (2 * (2 * radius + 1) if blur else 0) + (18 if settings.get("Sharpen", 0) else 0)
        if (
            self.gpu_adjustments_enabled
            and image.size <= 4_194_304
            and image.size * fetches <= 80_000_000
            and supports_gpu_adjustments(settings)
        ):
            self._pending_gpu = (generation, image, dict(settings), list(points), terrain)
            self.update()

    def cancel_gpu_request(self) -> None:
        self._pending_gpu = None

    def set_height_coloring(self, enabled: bool) -> None:
        """Toggle height-based terrain coloring in the fragment shader."""
        self.height_coloring = bool(enabled)
        self.update()

    def set_wireframe(self, enabled: bool) -> None:
        """Toggle wireframe rendering for the viewport."""
        self.wireframe = bool(enabled)
        self.update()

    def set_orthographic(self, enabled: bool) -> None:
        self.orthographic = bool(enabled)
        self.update()

    def set_grid_visible(self, enabled: bool) -> None:
        self.show_grid = bool(enabled)
        self.update()

    def set_camera_view(self, view: str, width: float = 100.0, depth: float = 100.0, height: float = 8.0) -> None:
        """Apply a named camera preset and optionally fit the model."""
        presets = {
            "top": self.camera.top_view,
            "front": self.camera.front_view,
            "side": self.camera.side_view,
            "isometric": self.camera.isometric_view,
            "reset": self.camera.reset,
        }
        if view == "fit":
            self.camera.fit_distance(width, depth, height, self.width() / max(1, self.height()))
            self.camera.target.setY((self.height_min_mm + self.height_max_mm) / 40.0)
        elif view in presets:
            presets[view]()
        else:
            raise ValueError(f"Unknown camera view: {view}")
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            self.last_position = event.position()
            self._drag_button = event.button()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:
        if self.last_position is not None:
            delta = event.position() - self.last_position
            if self._drag_button == Qt.MouseButton.MiddleButton:
                self.camera.pan(delta.x(), delta.y(), self.height())
            else:
                self.camera.orbit(delta.x(), delta.y())
            self.last_position = event.position()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            self.last_position = None
            self._drag_button = None
            self.unsetCursor()

    def wheelEvent(self, event) -> None:
        self.camera.zoom(event.angleDelta().y() / 120)
        self.update()

    def set_heightfield(self, heightfield: np.ndarray, width_mm: float = 100.0, depth_mm: float = 100.0) -> None:
        """Display a CPU-generated wire surface in physical millimeter coordinates."""
        width = float(width_mm)
        depth = float(depth_mm)
        if not math.isfinite(width) or not math.isfinite(depth) or width <= 0 or depth <= 0:
            raise ValueError("Viewport dimensions must be finite and positive")
        if heightfield.ndim != 2:
            raise ValueError("Heightfield must be 2D")
        if heightfield.shape[0] < 2 or heightfield.shape[1] < 2:
            raise ValueError("Heightfield must contain at least a 2x2 grid")
        if not np.isfinite(heightfield).all():
            raise ValueError("Heightfield values must be finite")
        # Keep the CPU heightfield authoritative; the viewport only needs a
        # display-resolution texture. Copying the full array here would double
        # the peak for a large heightfield and is unnecessary because the array
        # is treated as read-only by the viewport.
        self._pending_heightfield = (heightfield, width, depth)
        self._surface_extent = max(width, depth, float(np.ptp(heightfield))) / 20.0
        self.update()

    def _display_texture_limit(self) -> int:
        """Return the largest 2D texture edge the driver can accept.

        A preview texture does not need fabrication resolution. 4096 is the
        practical display ceiling on this class of GPU; the driver limit is
        checked so a smaller limit cannot fail the upload.
        """
        try:
            driver_limit = int(glGetIntegerv(GL_MAX_TEXTURE_SIZE))
        except Exception:
            driver_limit = 4096
        return max(1, min(4096, driver_limit))

    def _decimate_for_display(self, heightfield: np.ndarray) -> tuple[np.ndarray, int, int]:
        """Return an area-averaged display texture and its row/column counts.

        Stride sampling keeps only one sample per block, so a heightfield with
        detail near the stride frequency aliases into false low-frequency
        ridges in the viewport. Averaging each block (box filter) removes that
        aliasing and is the standard choice for downscaling. The CPU
        heightfield and every export path remain untouched; only the display
        texture is reduced.
        """
        limit = self._display_texture_limit()
        rows, columns = heightfield.shape
        if max(rows, columns) <= limit:
            return heightfield, rows, columns
        step = max(1, int(math.ceil(max(rows, columns) / limit)))
        target_rows = max(2, min(rows, int(round(rows / step))))
        target_columns = max(2, min(columns, int(round(columns / step))))
        display = _block_mean(heightfield, target_rows, target_columns)
        return display, display.shape[0], display.shape[1]

    def _upload_heightfield(self, heightfield: np.ndarray, width_mm: float, depth_mm: float) -> None:
        """Upload a pending surface while Qt's render context is current."""
        display, texture_rows, texture_columns = self._decimate_for_display(heightfield)
        self._sample_spacing = (
            width_mm / (20.0 * max(1, texture_columns - 1)),
            depth_mm / (20.0 * max(1, texture_rows - 1)),
        )
        self._gpu_surface = None
        self._ensure_surface_grid(texture_rows, texture_columns, width_mm, depth_mm)
        if not self.height_texture:
            self.height_texture = glGenTextures(1)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.height_texture)
        texture_data = np.ascontiguousarray(display.astype(np.float32) / 20.0)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_R32F, texture_columns, texture_rows, 0, GL_RED, GL_FLOAT, texture_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

    def _ensure_surface_grid(self, texture_rows: int, texture_columns: int, width_mm: float, depth_mm: float) -> None:
        preview_limit = 512
        rows, columns = min(texture_rows, preview_limit), min(texture_columns, preview_limit)
        grid_key = (rows, columns, width_mm, depth_mm)
        if grid_key != self._surface_grid_key:
            u = np.linspace(0, 1, columns, dtype=np.float32)
            v = np.linspace(0, 1, rows, dtype=np.float32)
            grid = np.zeros((rows, columns, 8), dtype=np.float32)
            grid[:, :, 0] = (u - 0.5) * width_mm / 20.0
            grid[:, :, 2] = (v[:, None] - 0.5) * depth_mm / 20.0
            grid[:, :, 4] = 1.0
            grid[:, :, 6] = u
            grid[:, :, 7] = v[:, None]
            indices = np.arange(rows * columns, dtype=np.int32).reshape(rows, columns)
            a = indices[:-1, :-1].ravel()
            b, d = a + 1, a + columns
            triangles = np.column_stack((a, d, b, b, d, d + 1)).ravel()
            surface_vertices = np.ascontiguousarray(grid.reshape(-1, 8)[triangles])
            if not self.surface_vao:
                self.surface_vao, self.surface_vbo = glGenVertexArrays(1), glGenBuffers(1)
            glBindVertexArray(self.surface_vao)
            glBindBuffer(GL_ARRAY_BUFFER, self.surface_vbo)
            glBufferData(GL_ARRAY_BUFFER, surface_vertices.nbytes, surface_vertices, GL_STATIC_DRAW)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 32, None)
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(12))
            glEnableVertexAttribArray(1)
            glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(24))
            glEnableVertexAttribArray(2)
            glBindVertexArray(0)
            self.surface_vertex_count = len(surface_vertices)
            self._surface_grid_key = grid_key

    def _prepare_gpu_surface(self, texture, image_shape, terrain) -> None:
        rows, columns = image_shape
        width, depth = terrain["width"], terrain["depth"]
        resolution = terrain["resolution"] or (columns, rows)
        self._ensure_surface_grid(max(2, resolution[1]), max(2, resolution[0]), width, depth)
        self._sample_spacing = (width / (20.0 * max(1, columns - 1)), depth / (20.0 * max(1, rows - 1)))
        self._surface_extent = max(width, depth, abs(terrain["maximum"] - terrain["minimum"])) / 20.0
        self._pending_heightfield = None
        if not self._mapping_texture:
            self._mapping_texture = glGenTextures(1)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self._mapping_texture)
        lut = np.ascontiguousarray(curve_lut(terrain["curve"]))
        glTexImage2D(GL_TEXTURE_2D, 0, GL_R32F, len(lut), 1, 0, GL_RED, GL_FLOAT, lut)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        self._gpu_surface = {**terrain, "texture": texture}
        if terrain["maximum"] > terrain["minimum"]:
            if terrain["sign"] < 0:
                self.height_min_mm, self.height_max_mm = -terrain["maximum"], -terrain["minimum"]
            else:
                self.height_min_mm, self.height_max_mm = terrain["minimum"], terrain["maximum"]

    def clear_heightfield(self) -> None:
        """Forget the current surface and any upload waiting for a context."""
        self._pending_heightfield = None
        self._pending_gpu = None
        self._gpu_surface = None
        self.surface_vertex_count = 0
        self._surface_grid_key = None
        self.update()

    def closeEvent(self, event) -> None:
        """Release context-owned resources before the widget is destroyed."""
        self._cleanup_gpu_resources()
        super().closeEvent(event)

    def _cleanup_gpu_resources(self) -> None:
        """Delete OpenGL objects while this widget's context is current."""
        if not self.context():
            return
        self.makeCurrent()
        try:
            if self._gpu_pipeline is not None:
                self._gpu_pipeline.close()
                self._gpu_pipeline = None
            if self.height_texture:
                glDeleteTextures([self.height_texture])
                self.height_texture = 0
            if self._mapping_texture:
                glDeleteTextures([self._mapping_texture])
                self._mapping_texture = 0
            self._gpu_surface = None
            buffers = [buffer for buffer in (self.vbo, self.surface_vbo) if buffer]
            if buffers:
                glDeleteBuffers(buffers)
            self.vbo = 0
            self.surface_vbo = 0
            arrays = [vao for vao in (self.vao, self.surface_vao) if vao]
            if arrays:
                glDeleteVertexArrays(arrays)
            self.vao = 0
            self.surface_vao = 0
            if self.program:
                glDeleteProgram(self.program)
                self.program = 0
            self.vertex_count = 0
            self.surface_vertex_count = 0
            self._surface_grid_key = None
            self._gl_ready = False
        finally:
            self.doneCurrent()

    def _program_from_files(self) -> int:
        def compile_shader(kind, path):
            shader = glCreateShader(kind)
            glShaderSource(shader, path.read_text())
            glCompileShader(shader)
            if not glGetShaderiv(shader, GL_COMPILE_STATUS):
                raise RuntimeError(glGetShaderInfoLog(shader).decode())
            return shader

        program = glCreateProgram()
        vertex = compile_shader(GL_VERTEX_SHADER, self.shader_dir / "test_grid.vert")
        fragment = compile_shader(GL_FRAGMENT_SHADER, self.shader_dir / "test_grid.frag")
        glAttachShader(program, vertex)
        glAttachShader(program, fragment)
        glLinkProgram(program)
        if not glGetProgramiv(program, GL_LINK_STATUS):
            raise RuntimeError(glGetProgramInfoLog(program).decode())
        glDeleteShader(vertex)
        glDeleteShader(fragment)
        return program
