"""Qt application setup for ClayField."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication

from clayfield.ui.main_window import MainWindow


def configure_opengl() -> None:
    """Request the documented OpenGL 3.3 core baseline."""
    format_ = QSurfaceFormat()
    format_.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    format_.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    format_.setVersion(3, 3)
    format_.setDepthBufferSize(24)
    format_.setStencilBufferSize(8)
    format_.setSwapInterval(1)
    QSurfaceFormat.setDefaultFormat(format_)


def run() -> int:
    """Create the application and enter the Qt event loop."""
    from clayfield import __version__

    if sys.argv[1:] == ["--version"]:
        print(f"ClayField {__version__}")
        return 0
    if sys.argv[1:] == ["--self-test"]:
        import numpy as np

        from clayfield.geometry.mesh_generator import generate_solid_mesh
        from clayfield.geometry.validation import validate_mesh

        resources = Path(__file__).resolve().parents[1] / "resources"
        for name in (
            "test_grid.vert",
            "test_grid.frag",
            "image_process.vert",
            "image_process.frag",
            "image_filter.frag",
        ):
            if not (resources / name).is_file():
                raise RuntimeError(f"Missing shader resource: {name}")
        mesh = generate_solid_mesh(np.array([[0, 1], [1, 2]], dtype=np.float32), 20, 20, 3)
        if not validate_mesh(mesh).valid:
            raise RuntimeError("Mesh self-test failed")
        print(f"ClayField {__version__} self-test passed")
        return 0
    if sys.argv[1:] == ["--gl-self-test"]:
        import numpy as np
        from PySide6.QtCore import QTimer

        from clayfield.ui.viewport import Viewport

        configure_opengl()
        application = QApplication([sys.argv[0]])
        viewport = Viewport()
        failures = []
        viewport.initialization_failed.connect(failures.append)
        viewport.resize(640, 480)
        viewport.set_heightfield(np.array([[0, 8], [0, 8]], dtype=np.float32))
        viewport.show()

        def finish_gl_test():
            frame = viewport.grabFramebuffer()
            vertex_count = viewport.surface_vertex_count
            surface_pixels = np.frombuffer(frame.bits(), dtype=np.uint8).copy() if not frame.isNull() else np.array([])
            viewport.clear_heightfield()
            empty_frame = viewport.grabFramebuffer()
            empty_pixels = (
                np.frombuffer(empty_frame.bits(), dtype=np.uint8) if not empty_frame.isNull() else np.array([])
            )
            changed = (
                int(np.count_nonzero(surface_pixels != empty_pixels))
                if surface_pixels.shape == empty_pixels.shape
                else 0
            )
            gpu_error = float("inf")
            try:
                from clayfield.image.pipeline import apply_adjustments
                from clayfield.ui.gpu_pipeline import GpuImagePipeline

                image = np.array([[0.0, 0.2, 1.0], [0.8, 0.5, 0.1]], dtype=np.float32)
                settings = {"Gamma": 1.4, "Brightness": 0.1, "inverted": True}
                points = [(0.0, 0.0), (0.5, 0.3), (1.0, 1.0)]
                viewport.makeCurrent()
                pipeline = GpuImagePipeline()
                try:
                    gpu_error = float(
                        np.max(
                            np.abs(
                                pipeline.process(image, settings, points) - apply_adjustments(image, settings, points)
                            )
                        )
                    )
                finally:
                    pipeline.close()
                    viewport.doneCurrent()
            except Exception as error:
                failures.append(f"GPU processing failed: {error}")
            success = not failures and viewport.isValid() and vertex_count > 0 and changed > 100 and gpu_error <= 0.001
            print(
                f"OpenGL {viewport.version}; terrain vertices: {vertex_count}; changed pixel channels: {changed}; GPU error: {gpu_error:.6f}"
            )
            if failures:
                print("; ".join(failures), file=sys.stderr)
            application.exit(0 if success else 1)

        QTimer.singleShot(1000, finish_gl_test)
        return application.exec()
    configure_opengl()
    application = QApplication(sys.argv)
    application.setApplicationName("ClayField")
    application.setApplicationVersion(__version__)
    application.setOrganizationName("ClayField")
    window = MainWindow()
    window.show()
    return application.exec()
