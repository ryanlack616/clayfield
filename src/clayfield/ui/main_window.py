"""Main ClayField application window."""

from __future__ import annotations

from pathlib import Path
from copy import copy, deepcopy

import numpy as np

from PySide6.QtCore import QSettings, QThreadPool, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QDialog, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QMainWindow, QMessageBox, QProgressBar, QScrollArea, QSplitter, QStatusBar, QToolButton, QVBoxLayout
from clayfield.app.project_io import ProjectIOError, load_project, save_project
from clayfield.app.history import ParameterHistory, restore_parameters
from clayfield.app.presets import PresetError, load_preset, save_preset
from clayfield.app.recovery import discard_recovery_snapshot, find_recovery_snapshots, prepare_recovery_snapshot
from clayfield.app.worker import FunctionWorker
from clayfield.export.tasks import analyze_image_export_task, analyze_procedural_export_task, export_heightmap_task, export_mesh_task, export_procedural_heightmap_task, export_procedural_mesh_task
from clayfield.field.persistence import PipelineSnapshot, SourceDescriptor
from clayfield.field.model import FieldMetadata, NormalizedField
from clayfield.field.processing import FieldProcessingSettings
from clayfield.field.workflow import evaluate_serialized_pipeline
from clayfield.terrain.mapping import MappingSettings
from clayfield.terrain.fabrication import FabricationProfile, analyze_heightfield
from clayfield.geometry.container import ContainerSettings

from clayfield.app.project_state import ProjectState
from clayfield.ui.image_panel import ImagePanel
from clayfield.ui.terrain_panel import TerrainPanel
from clayfield.ui.viewport import Viewport
from clayfield.ui.theme import apply_theme
from clayfield.ui.export_preview import ExportPreviewDialog
from clayfield.ui.cross_section import CrossSectionDialog
from clayfield.terrain.heightfield import PhysicalDimensions, generate_physical_heightfield, options_from_state, physical_height_bounds


class MainWindow(QMainWindow):
    """Compose the image, terrain, and OpenGL viewport panels."""

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.state = ProjectState()
        self.history = ParameterHistory(self.state)
        self.thread_pool = QThreadPool.globalInstance()
        self._heightfield_generation = 0
        self._heightfield_workers = {}
        self._heightfield_key = None
        self._heightfield_image = None
        self._procedural_key = None
        self._export_active = False
        self._active_worker = None
        self._recovery_snapshot = None
        self._revision = 0
        self._autosave_worker = None
        self._settings = QSettings("ClayField", "ClayField")
        apply_theme(self._settings.value("dark_theme", False, type=bool))
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(30_000)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()
        self.setWindowTitle("ClayField — Untitled")
        self.resize(1280, 820)
        self.setStatusBar(QStatusBar(self))
        self.export_progress = QProgressBar(self)
        self.export_progress.setRange(0, 100)
        self.export_progress.setMaximumWidth(180)
        self.export_progress.hide()
        self.statusBar().addPermanentWidget(self.export_progress)
        self.viewport = Viewport(self)
        self.image_panel = ImagePanel(self.state, self)
        self.terrain_panel = TerrainPanel(self.state, self)
        self._build_canvas_overlays()
        self.image_panel.image_loaded.connect(self._image_loaded)
        self.image_panel.preview_availability_changed.connect(self._set_preview_overlay)
        self.image_panel.image_geometry_changed.connect(self.terrain_panel.update_aspect_ratio)
        self.image_panel.error_occurred.connect(self._show_error)
        self.image_panel.parameters_changed.connect(self._mark_dirty)
        self.image_panel.processing_started.connect(self._invalidate_heightfield)
        self.image_panel.processing_started.connect(self.viewport.cancel_gpu_request)
        self.image_panel.adjusted_image_ready.connect(self._rebuild_heightfield)
        self.image_panel.adjusted_image_ready.connect(self.viewport.cancel_gpu_request)
        self.image_panel.procedural_source_changed.connect(self._rebuild_heightfield)
        self.image_panel.gpu_adjustment_requested.connect(self._request_gpu_adjustments)
        self.viewport.gpu_adjustments_ready.connect(self._gpu_preview_ready)
        self.viewport.gpu_error.connect(self._gpu_preview_failed)
        self.viewport.initialization_failed.connect(lambda message: QTimer.singleShot(0, lambda: self._show_error(message)))
        self.terrain_panel.parameters_changed.connect(self._mark_dirty)
        self.terrain_panel.parameters_changed.connect(self._rebuild_heightfield)
        self.terrain_panel.parameters_changed.connect(self.image_panel._update_provenance)
        splitter = QSplitter()
        image_scroll = QScrollArea()
        image_scroll.setWidgetResizable(True)
        image_scroll.setWidget(self.image_panel)
        terrain_scroll = QScrollArea()
        terrain_scroll.setWidgetResizable(True)
        terrain_scroll.setWidget(self.terrain_panel)
        splitter.addWidget(image_scroll)
        splitter.addWidget(self.viewport)
        splitter.addWidget(terrain_scroll)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)
        self._build_menus()
        self._offer_recovery()
        self.statusBar().showMessage("Ready — ClayField")

    def _build_canvas_overlays(self) -> None:
        """Keep inspection and composition controls on top of the 3D canvas."""
        self.preview_overlay = QFrame(self.viewport)
        self.preview_overlay.setObjectName("canvasOverlay")
        self.preview_overlay.setFrameShape(QFrame.Shape.StyledPanel)
        preview_layout = QVBoxLayout(self.preview_overlay)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.addWidget(self.image_panel.preview)
        self.preview_overlay.setFixedSize(292, 220)
        self.preview_overlay.hide()

        self.compose_overlay = QFrame(self.viewport)
        self.compose_overlay.setObjectName("canvasOverlay")
        self.compose_overlay.setFrameShape(QFrame.Shape.StyledPanel)
        compose_layout = QVBoxLayout(self.compose_overlay)
        compose_layout.setContentsMargins(10, 8, 10, 10)
        header = QHBoxLayout()
        title = QLabel("COMPOSE / SECOND FIELD")
        close = QToolButton()
        close.setText("×")
        close.setToolTip("Close compose controls")
        close.clicked.connect(lambda: self.image_panel.compose_toggle.setChecked(False))
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close)
        compose_layout.addLayout(header)
        compose_layout.addWidget(self.image_panel.composition_controls["box"])
        compose_layout.addWidget(QLabel("External sources"))
        compose_layout.addWidget(self.image_panel.external_status)
        self.compose_overlay.setFixedWidth(390)
        self.compose_overlay.setStyleSheet(
            "QFrame#canvasOverlay { background-color: #14171a; border: 1px solid #3d464e; }"
        )
        self.preview_overlay.setStyleSheet(
            "QFrame#canvasOverlay { background-color: #14171a; border: 1px solid #3d464e; }"
        )
        self.compose_overlay.hide()
        self.image_panel.composition_requested.connect(self._set_compose_overlay)
        self._position_canvas_overlays()

    def _set_compose_overlay(self, visible: bool) -> None:
        self.compose_overlay.setVisible(visible)
        if visible:
            self.compose_overlay.adjustSize()
            self._position_canvas_overlays()

    def _set_preview_overlay(self, visible: bool) -> None:
        self.preview_overlay.setVisible(visible)
        if visible:
            self._position_canvas_overlays()

    def _position_canvas_overlays(self) -> None:
        if not hasattr(self, "preview_overlay"):
            return
        margin = 12
        self.preview_overlay.move(margin, margin)
        if self.compose_overlay.isVisible():
            self.compose_overlay.move(max(margin, self.viewport.width() - self.compose_overlay.width() - margin), margin)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_canvas_overlays()

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        for label, callback in (("New Project", self._new_project), ("Open Project", self._open_project), ("Save Project", self._save_project), ("Save Project As…", self._save_project_as), ("Export STL", self._export_stl), ("Export 3MF", self._export_3mf), ("Export Heightmap", self._export_heightmap), ("Exit", self.close)):
            action = file_menu.addAction(label)
            action.triggered.connect(callback)
        self.recent_menu = file_menu.addMenu("Recent Projects")
        self.recent_menu.aboutToShow.connect(self._populate_recent)
        edit_menu = self.menuBar().addMenu("Edit")
        self.undo_action = edit_menu.addAction("Undo")
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self._undo)
        self.redo_action = edit_menu.addAction("Redo")
        self.redo_action.setShortcut("Ctrl+Shift+Z")
        self.redo_action.triggered.connect(self._redo)
        edit_menu.addSeparator()
        save_preset_action = edit_menu.addAction("Save Adjustment/Terrain Preset…")
        save_preset_action.triggered.connect(self._save_preset)
        load_preset_action = edit_menu.addAction("Load Adjustment/Terrain Preset…")
        load_preset_action.triggered.connect(self._load_preset)
        self._update_history_actions()
        view_menu = self.menuBar().addMenu("View")
        for label, view in (("Reset Camera", "reset"), ("Fit Terrain", "fit"), ("Top View", "top"), ("Front View", "front"), ("Side View", "side"), ("Isometric View", "isometric")):
            action = view_menu.addAction(label)
            action.triggered.connect(lambda checked=False, selected=view: self._camera_view(selected))
        wireframe = view_menu.addAction("Wireframe")
        wireframe.setCheckable(True)
        wireframe.toggled.connect(self.viewport.set_wireframe)
        orthographic = view_menu.addAction("Orthographic Projection")
        orthographic.setCheckable(True)
        orthographic.toggled.connect(self.viewport.set_orthographic)
        grid = view_menu.addAction("Show Grid")
        grid.setCheckable(True)
        grid.setChecked(True)
        grid.toggled.connect(self.viewport.set_grid_visible)
        dark_theme = view_menu.addAction("Dark Theme")
        dark_theme.setCheckable(True)
        dark_theme.setChecked(True)
        dark_theme.toggled.connect(self._set_dark_theme)
        height_coloring = view_menu.addAction("Height Coloring")
        height_coloring.setCheckable(True)
        height_coloring.toggled.connect(self.viewport.set_height_coloring)
        self.gpu_preview_action = view_menu.addAction("GPU Image Preview")
        self.gpu_preview_action.setCheckable(True)
        self.gpu_preview_action.setChecked(True)
        self.gpu_preview_action.toggled.connect(self._set_gpu_preview)
        color = view_menu.addAction("Surface Color…")
        color.triggered.connect(self._choose_surface_color)
        light = view_menu.addAction("Lighting Direction…")
        light.triggered.connect(self._choose_light_direction)
        cross_section = view_menu.addAction("Cross-section…")
        cross_section.triggered.connect(self._show_cross_section)
        operation_menu = self.menuBar().addMenu("Operations")
        cancel = operation_menu.addAction("Cancel Current Operation")
        cancel.triggered.connect(self._cancel_current_operation)

    def dragEnterEvent(self, event) -> None:
        """Accept local ClayField project files dragged onto the window."""
        if any(
            url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() == ".clayfield"
            for url in event.mimeData().urls()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        """Open the first dropped ClayField project."""
        for url in event.mimeData().urls():
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() == ".clayfield":
                if not self._confirm_project_change():
                    event.ignore()
                    return
                try:
                    load_project(url.toLocalFile(), self.state)
                    self._revision += 1
                    self.image_panel.cancel_pending_load()
                    self._invalidate_heightfield()
                    self.viewport.clear_heightfield()
                    self._remember_project(self.state.project_path)
                    self.image_panel.refresh_from_state()
                    self.terrain_panel.sync_from_state()
                    if self.state.source_type != "image":
                        self._rebuild_procedural_heightfield()
                    self.history.reset(self.state, clean=True)
                    self._update_history_actions()
                    self.setWindowTitle(f"ClayField — {self.state.project_path.name}")
                    event.acceptProposedAction()
                except ProjectIOError as error:
                    self._show_error(str(error))
                    event.ignore()
                return
        event.ignore()

    def _new_project(self) -> None:
        if not self._confirm_project_change():
            return
        self._invalidate_heightfield()
        self._revision += 1
        self.state.__dict__.update(ProjectState().__dict__)
        self.image_panel.clear_preview()
        self.terrain_panel.sync_from_state()
        self.history.reset(self.state, clean=True)
        self._update_history_actions()
        self.viewport.clear_heightfield()
        self.setWindowTitle("ClayField — Untitled")

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open ClayField Project", "", "ClayField projects (*.clayfield)")
        if not path:
            return
        self._open_project_path(path)

    def _open_project_path(self, path: str) -> None:
        if not self._confirm_project_change():
            return
        try:
            load_project(path, self.state)
            self._revision += 1
            self.image_panel.cancel_pending_load()
            self._invalidate_heightfield()
            self.viewport.clear_heightfield()
            self._remember_project(self.state.project_path)
            self.image_panel.refresh_from_state()
            self.terrain_panel.sync_from_state()
            if self.state.source_type != "image":
                self._rebuild_procedural_heightfield()
            self.history.reset(self.state, clean=True)
            self._update_history_actions()
            # Adjustment completion triggers heightfield generation in order.
            self.setWindowTitle(f"ClayField — {self.state.project_path.name}")
        except ProjectIOError as error:
            self._show_error(str(error))

    def _save_project(self) -> None:
        self._save_project_to(self.state.project_path)

    def _save_project_as(self) -> None:
        self._save_project_to(None)

    def _save_project_to(self, current_path) -> None:
        previous_path = self.state.project_path
        path = str(current_path) if current_path else ""
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, "Save ClayField Project", "project.clayfield", "ClayField projects (*.clayfield)")
        if not path:
            return
        try:
            output = save_project(self.state, path)
        except ProjectIOError as error:
            self._show_error(str(error))
            return
        self.state.dirty = False
        self._revision += 1
        self.history.record(self.state)
        self.history.mark_clean()
        self._update_history_actions()
        self._remember_project(output)
        discard_recovery_snapshot(previous_path)
        if previous_path != output:
            discard_recovery_snapshot(output)
        self._discard_recovered_snapshot()
        self.setWindowTitle(f"ClayField — {output.name}")
        self.statusBar().showMessage(f"Saved project: {output}")

    def _rebuild_heightfield(self) -> None:
        if self.state.source_type == "image" and self.state.composition_settings.get("enabled") and self.state.secondary_source_descriptor is not None:
            self._rebuild_composed_image_heightfield()
            return
        if self.state.source_type != "image":
            self._rebuild_procedural_heightfield()
            return
        image = self.state.adjusted_image
        if image is None:
            return
        state = self.state
        key = (state.terrain_width_mm, state.terrain_depth_mm, state.minimum_height_mm, state.maximum_height_mm,
               state.heightfield_resolution, state.height_invert, state.smoothing_sigma, state.edge_falloff,
               state.height_mapping_gamma, state.noise_amplitude, state.noise_frequency, state.noise_seed,
               tuple(state.mapping_curve_points), state.edge_falloff_mode, state.relief_mode, options_from_state(state))
        if image is self._heightfield_image and key == self._heightfield_key:
            return
        self._heightfield_key, self._heightfield_image = key, image
        self._heightfield_generation += 1
        self.state.physical_heightfield = None
        self.image_panel.set_heightfield_preview(None)
        token = self._heightfield_generation
        self._start_heightfield_worker(image, token, provisional=False)

    def _procedural_snapshot(self, *, source_already_processed: bool = False) -> PipelineSnapshot:
        descriptor = SourceDescriptor.from_dict(self.state.source_descriptor)
        settings = self.state.adjustment_settings
        processing = FieldProcessingSettings(
            black_point=float(settings.get("Black point", 0.0)),
            input_gamma=float(settings.get("Gamma", 1.0)),
            white_point=float(settings.get("White point", 1.0)),
            output_black=float(settings.get("Output black", 0.0)),
            output_white=float(settings.get("Output white", 1.0)),
            curve_points=tuple(tuple(point) for point in self.state.curve_points),
            curve_interpolation=str(settings.get("Curve interpolation", "linear")),
            brightness=float(settings.get("Brightness", 0.0)),
            contrast=float(settings.get("Contrast", 1.0)),
            threshold_enabled=bool(settings.get("threshold_enabled", False)),
            threshold_cutoff=float(settings.get("Threshold", 0.5)),
            blur_radius=float(self.state.smoothing_sigma),
        )
        if source_already_processed:
            processing = FieldProcessingSettings()
        mapping = MappingSettings(
            minimum_height_mm=self.state.minimum_height_mm,
            maximum_height_mm=self.state.maximum_height_mm,
            gamma=self.state.height_mapping_gamma,
            inverted=self.state.height_invert,
            clamp_min=self.state.height_clamp_min,
            clamp_max=self.state.height_clamp_max,
            edge_falloff=self.state.edge_falloff,
            edge_strength=self.state.edge_falloff_strength,
            edge_falloff_mode=self.state.edge_falloff_mode,
            offset_mm=self.state.height_offset_mm,
            scale=self.state.height_scale,
            mapping_curve_points=tuple(tuple(point) for point in self.state.mapping_curve_points),
        )
        secondary = SourceDescriptor.from_dict(self.state.secondary_source_descriptor) if self.state.secondary_source_descriptor is not None else None
        mask = SourceDescriptor.from_dict(self.state.mask_source_descriptor) if self.state.mask_source_descriptor is not None else None
        snapshot = PipelineSnapshot.from_settings(
            descriptor,
            processing,
            secondary_processing=FieldProcessingSettings(**self.state.secondary_processing_settings) if self.state.secondary_processing_settings else None,
            mapping=mapping,
            secondary_source=secondary,
            mask_source=mask,
            composition=self.state.composition_settings,
        )
        self.state.pipeline_snapshot = snapshot.to_dict()
        return snapshot

    def _rebuild_composed_image_heightfield(self) -> None:
        image = self.state.adjusted_image
        if image is None:
            return
        try:
            snapshot = self._procedural_snapshot(source_already_processed=True)
            primary = NormalizedField(np.asarray(image, dtype=np.float32), FieldMetadata("image", "adjusted_image", "1"))
        except (TypeError, ValueError) as error:
            self._show_error(f"Image composition is invalid: {error}")
            return
        resolution = self.state.heightfield_resolution or (image.shape[1], image.shape[0])
        self._heightfield_generation += 1
        token = self._heightfield_generation
        self.state.physical_heightfield = None
        self.image_panel.set_heightfield_preview(None)
        worker = FunctionWorker(
            evaluate_serialized_pipeline,
            snapshot,
            (resolution[1], resolution[0]),
            primary_field=primary,
            external_fields=self._external_fields(),
            inject_control=True,
        )
        self._heightfield_workers[token] = worker
        worker.signals.progress.connect(lambda percent, message: self.statusBar().showMessage(f"Image composition: {percent}% — {message}"))
        worker.signals.finished.connect(lambda result, generation=token: self._procedural_finished(generation, result))
        worker.signals.failed.connect(lambda message, generation=token: self._procedural_failed(generation, message))
        worker.signals.cancelled.connect(lambda generation=token: self._heightfield_workers.pop(generation, None))
        self.thread_pool.start(worker)

    def _external_fields(self) -> dict[str, NormalizedField]:
        fields: dict[str, NormalizedField] = {}
        for values, descriptor_data in ((self.state.secondary_field, self.state.secondary_source_descriptor), (self.state.mask_field, self.state.mask_source_descriptor)):
            if values is None or descriptor_data is None:
                continue
            descriptor = SourceDescriptor.from_dict(descriptor_data)
            if descriptor.content_hash is not None:
                fields[descriptor.content_hash] = NormalizedField(np.asarray(values, dtype=np.float32), FieldMetadata("external", "embedded_field", "1"))
        return fields

    def _container_settings(self) -> ContainerSettings:
        return ContainerSettings(
            mode=self.state.container_mode,
            wall_thickness_mm=self.state.container_wall_thickness_mm,
            clearance_above_model_mm=self.state.container_clearance_mm,
            outside_dimensions=self.state.container_outside_dimensions,
        )

    def _final_export_analysis(self):
        if self.state.source_type == "image" and not self.state.composition_settings.get("enabled"):
            if self.state.adjusted_image is None:
                return None
            dimensions = PhysicalDimensions(self.state.terrain_width_mm, self.state.terrain_depth_mm, self.state.minimum_height_mm, self.state.maximum_height_mm)
            return (
                analyze_image_export_task,
                (self.state.adjusted_image.copy(), dimensions, self.state.export_resolution, self.state.base_thickness_mm, self.state.relief_mode, self.state.smoothing_sigma, self.state.edge_falloff, self.state.height_invert, self.state.height_mapping_gamma, self.state.noise_amplitude, self.state.noise_frequency, self.state.noise_seed, list(self.state.mapping_curve_points), self.state.edge_falloff_mode),
                {"height_options": options_from_state(self.state), "profile": FabricationProfile(**self.state.fabrication_profile)},
            )
        try:
            snapshot = self._procedural_snapshot(source_already_processed=self.state.source_type == "image")
        except (TypeError, ValueError) as error:
            self._show_error(f"Export analysis is invalid: {error}")
            return None
        primary = None
        if self.state.source_type == "image":
            if self.state.adjusted_image is None:
                return None
            primary = NormalizedField(np.asarray(self.state.adjusted_image, dtype=np.float32), FieldMetadata("image", "adjusted_image", "1"))
        return (
            analyze_procedural_export_task,
            (snapshot, self.state.export_resolution, self.state.terrain_width_mm, self.state.terrain_depth_mm, self.state.base_thickness_mm, self.state.relief_mode),
            {"external_fields": self._external_fields(), "primary_field": primary, "profile": FabricationProfile(**self.state.fabrication_profile)},
        )

    def _rebuild_procedural_heightfield(self) -> None:
        try:
            snapshot = self._procedural_snapshot()
        except (TypeError, ValueError) as error:
            self._show_error(f"Procedural source is invalid: {error}")
            return
        resolution = self.state.heightfield_resolution or (512, 512)
        key = (
            self.state.source_type,
            repr(snapshot.to_dict()),
            resolution,
            self.state.terrain_width_mm,
            self.state.terrain_depth_mm,
            self.state.relief_mode,
        )
        if key == self._procedural_key and self.state.physical_heightfield is not None:
            return
        self._procedural_key = key
        self._heightfield_generation += 1
        token = self._heightfield_generation
        self.state.physical_heightfield = None
        self.image_panel.set_heightfield_preview(None)
        worker = FunctionWorker(evaluate_serialized_pipeline, snapshot, (resolution[1], resolution[0]), external_fields=self._external_fields(), inject_control=True)
        self._heightfield_workers[token] = worker
        worker.signals.progress.connect(lambda percent, message: self.statusBar().showMessage(f"Procedural field: {percent}% — {message}"))
        worker.signals.finished.connect(lambda result, generation=token: self._procedural_finished(generation, result))
        worker.signals.failed.connect(lambda message, generation=token: self._procedural_failed(generation, message))
        worker.signals.cancelled.connect(lambda generation=token: self._heightfield_workers.pop(generation, None))
        self.thread_pool.start(worker)

    def _procedural_finished(self, generation: int, result) -> None:
        self._heightfield_workers.pop(generation, None)
        if generation != self._heightfield_generation:
            return
        physical = result.physical_heightfield
        self.state.physical_heightfield = physical
        self.image_panel.set_procedural_preview(result.normalized_field.values)
        display = -physical if self.state.relief_mode == "negative" else physical
        self.viewport.set_height_range(float(display.min()), float(display.max()))
        self.viewport.set_heightfield(display, self.state.terrain_width_mm, self.state.terrain_depth_mm)
        self.image_panel.set_heightfield_preview(display)
        self.terrain_panel.set_actual_height_range(float(display.min()), float(display.max()))
        self.terrain_panel.set_fabrication_metrics(
            analyze_heightfield(display, self.state.terrain_width_mm, self.state.terrain_depth_mm, self.state.base_thickness_mm, "positive", profile=FabricationProfile(**self.state.fabrication_profile))
        )
        self.statusBar().showMessage("Procedural field ready")

    def _procedural_failed(self, generation: int, message: str) -> None:
        self._heightfield_workers.pop(generation, None)
        if generation == self._heightfield_generation:
            self._show_error(f"Procedural field failed: {message}")

    def _gpu_preview_ready(self, generation: int, image) -> None:
        if image is None or generation != self.image_panel._adjustment_generation or self.state.adjusted_image is not None:
            return
        self._heightfield_generation += 1
        self._start_heightfield_worker(image, self._heightfield_generation, provisional=True)

    def _request_gpu_adjustments(self, generation, image, settings, points) -> None:
        state = self.state
        if state.smoothing_sigma or state.noise_amplitude or state.edge_falloff or state.height_invert or state.height_normalize or state.height_clamp_min != 0 or state.height_clamp_max != 1:
            return
        if state.maximum_height_mm < state.minimum_height_mm:
            return
        dimensions = PhysicalDimensions(state.terrain_width_mm, state.terrain_depth_mm, state.minimum_height_mm, state.maximum_height_mm)
        minimum, maximum = physical_height_bounds(dimensions, options_from_state(state))
        terrain = {
            "width": state.terrain_width_mm, "depth": state.terrain_depth_mm,
            "minimum": minimum, "maximum": maximum,
            "resolution": state.heightfield_resolution,
            "gamma": state.height_mapping_gamma, "curve": list(state.mapping_curve_points),
            "sign": -1.0 if state.relief_mode == "negative" else 1.0,
        }
        self.viewport.request_gpu_adjustments(generation, image, settings, points, terrain)

    def _start_heightfield_worker(self, image, token: int, provisional: bool) -> None:
        dimensions = PhysicalDimensions(self.state.terrain_width_mm, self.state.terrain_depth_mm, self.state.minimum_height_mm, self.state.maximum_height_mm)
        options = options_from_state(self.state)
        resolution = self.state.heightfield_resolution
        if resolution is None and min(image.shape[:2]) < 2:
            resolution = (max(2, image.shape[1]), max(2, image.shape[0]))
        worker = FunctionWorker(generate_physical_heightfield, image.copy(), dimensions, resolution, self.state.height_invert, self.state.smoothing_sigma, self.state.edge_falloff, self.state.height_mapping_gamma, self.state.noise_amplitude, self.state.noise_frequency, self.state.noise_seed, list(self.state.mapping_curve_points), self.state.edge_falloff_mode, options=options)
        self._heightfield_workers[token] = worker
        worker.signals.finished.connect(lambda result, generation=token, dims=dimensions, mode=self.state.relief_mode, preview=provisional, opts=options: self._heightfield_finished(generation, dims, result, mode, preview, opts))
        worker.signals.failed.connect(lambda message, generation=token: self._heightfield_failed(generation, message))
        self.thread_pool.start(worker)

    def _invalidate_heightfield(self) -> None:
        self._heightfield_generation += 1
        self._heightfield_key = None
        self._heightfield_image = None
        self._procedural_key = None
        self.state.physical_heightfield = None
        self.image_panel.set_heightfield_preview(None)

    def _heightfield_finished(self, generation: int, dimensions: PhysicalDimensions, heightfield, mode: str = "positive", provisional: bool = False, options=None) -> None:
        self._heightfield_workers.pop(generation, None)
        if generation != self._heightfield_generation:
            return
        if not provisional:
            self.state.physical_heightfield = heightfield
        display = -heightfield if mode == "negative" else heightfield
        low, high = physical_height_bounds(dimensions, options or options_from_state(self.state))
        minimum, maximum = (-high, -low) if mode == "negative" else (low, high)
        if maximum > minimum:
            self.viewport.set_height_range(minimum, maximum)
        self.viewport.set_heightfield(display, dimensions.width_mm, dimensions.depth_mm)
        if not provisional:
            self.image_panel.set_heightfield_preview(display)
            self.terrain_panel.set_actual_height_range(float(display.min()), float(display.max()))
            self.terrain_panel.set_fabrication_metrics(
                analyze_heightfield(display, dimensions.width_mm, dimensions.depth_mm, self.state.base_thickness_mm, "positive", profile=FabricationProfile(**self.state.fabrication_profile))
            )

    def _heightfield_failed(self, generation: int, message: str) -> None:
        self._heightfield_workers.pop(generation, None)
        if generation == self._heightfield_generation:
            self._heightfield_key = None
            self._show_error(message)

    def _export_stl(self) -> None:
        self._start_mesh_export("STL", "relief.stl", "STL files (*.stl)", "stl")

    def _export_3mf(self) -> None:
        self._start_mesh_export("3MF", "relief.3mf", "3MF files (*.3mf)", "3mf")

    def _start_mesh_export(self, label: str, default_name: str, file_filter: str, file_type: str) -> None:
        image = self.state.adjusted_image
        procedural = self.state.source_type != "image"
        if (image is None and not procedural) or self._export_active:
            self.statusBar().showMessage("No source available or another export is running")
            return
        if self.state.physical_heightfield is None:
            self.statusBar().showMessage("Wait for the terrain preview to finish")
            return
        if ExportPreviewDialog(self.state, label, self, final_analysis=self._final_export_analysis()).exec() != QDialog.DialogCode.Accepted:
            return
        path, _ = QFileDialog.getSaveFileName(self, f"Export {label}", default_name, file_filter)
        if not path:
            return
        extension = ".stl" if file_type == "stl" else ".3mf"
        if Path(path).suffix.lower() != extension:
            path += extension
        dimensions = PhysicalDimensions(self.state.terrain_width_mm, self.state.terrain_depth_mm, self.state.minimum_height_mm, self.state.maximum_height_mm)
        self._export_active = True
        self.export_progress.setValue(0)
        self.export_progress.show()
        if procedural:
            worker = FunctionWorker(export_procedural_mesh_task, self._procedural_snapshot(), dimensions, self.state.export_resolution, self.state.base_thickness_mm, self.state.relief_mode, path, file_type, external_fields=self._external_fields(), container_settings=self._container_settings(), inject_control=True)
        else:
            worker = FunctionWorker(export_mesh_task, image.copy(), dimensions, self.state.export_resolution, self.state.base_thickness_mm, self.state.relief_mode, path, file_type, self.state.smoothing_sigma, self.state.edge_falloff, self.state.height_invert, self.state.height_mapping_gamma, self.state.noise_amplitude, self.state.noise_frequency, self.state.noise_seed, list(self.state.mapping_curve_points), self.state.edge_falloff_mode, height_options=options_from_state(self.state), container_settings=self._container_settings(), inject_control=True)
        self._active_worker = worker
        worker.signals.progress.connect(lambda percent, message: self._export_progress(label, percent, message))
        worker.signals.finished.connect(lambda output: self._export_finished(label, output))
        worker.signals.failed.connect(lambda message: self._export_failed(label, message))
        worker.signals.cancelled.connect(lambda: self._export_cancelled(label))
        self.thread_pool.start(worker)

    def _export_heightmap(self) -> None:
        image = self.state.adjusted_image
        procedural = self.state.source_type != "image"
        if (image is None and not procedural) or self._export_active:
            self.statusBar().showMessage("No source available or another export is running")
            return
        if self.state.physical_heightfield is None:
            self.statusBar().showMessage("Wait for the terrain preview to finish")
            return
        if ExportPreviewDialog(self.state, "Heightmap", self, mesh=False, final_analysis=self._final_export_analysis()).exec() != QDialog.DialogCode.Accepted:
            return
        path, selected = QFileDialog.getSaveFileName(self, "Export Heightmap", "heightmap.png", "PNG 16-bit (*.png);;PNG 8-bit (*.png);;TIFF 16-bit (*.tif *.tiff);;TIFF 8-bit (*.tif *.tiff)")
        if not path:
            return
        if not Path(path).suffix:
            path += ".tif" if selected.startswith("TIFF") else ".png"
        dimensions = PhysicalDimensions(self.state.terrain_width_mm, self.state.terrain_depth_mm, self.state.minimum_height_mm, self.state.maximum_height_mm)
        self._export_active = True
        self.export_progress.setValue(0)
        self.export_progress.show()
        bit_depth = 8 if "8-bit" in selected else 16
        if procedural:
            worker = FunctionWorker(export_procedural_heightmap_task, self._procedural_snapshot(), self.state.export_resolution, path, bit_depth, external_fields=self._external_fields(), relief_mode=self.state.relief_mode, inject_control=True)
        else:
            worker = FunctionWorker(export_heightmap_task, image.copy(), dimensions, self.state.export_resolution, path, bit_depth, self.state.smoothing_sigma, self.state.edge_falloff, self.state.height_invert, self.state.height_mapping_gamma, self.state.noise_amplitude, self.state.noise_frequency, self.state.noise_seed, list(self.state.mapping_curve_points), self.state.edge_falloff_mode, relief_mode=self.state.relief_mode, height_options=options_from_state(self.state), inject_control=True)
        self._active_worker = worker
        worker.signals.progress.connect(lambda percent, message: self._export_progress("Heightmap", percent, message))
        worker.signals.finished.connect(lambda output: self._export_finished("Heightmap", output))
        worker.signals.failed.connect(lambda message: self._export_failed("Heightmap", message))
        worker.signals.cancelled.connect(lambda: self._export_cancelled("Heightmap"))
        self.thread_pool.start(worker)

    def _export_progress(self, label: str, percent: int, message: str) -> None:
        self.export_progress.setValue(percent)
        self.statusBar().showMessage(f"{label}: {percent}% — {message}")

    def _export_finished(self, label: str, output) -> None:
        self._export_active = False
        self._active_worker = None
        self.export_progress.hide()
        self.statusBar().showMessage(f"Exported {label}: {output}")

    def _export_failed(self, label: str, message: str) -> None:
        self._export_active = False
        self._active_worker = None
        self.export_progress.hide()
        self._show_error(f"{label} export failed: {message}")

    def _export_cancelled(self, label: str) -> None:
        self._export_active = False
        self._active_worker = None
        self.export_progress.hide()
        self.statusBar().showMessage(f"Cancelled {label} export")

    def _autosave(self) -> None:
        if not self.state.dirty or self._autosave_worker is not None:
            return
        # Source pixels are immutable after loading; copy only mutable settings.
        snapshot = copy(self.state)
        snapshot.adjustment_settings = deepcopy(self.state.adjustment_settings)
        snapshot.curve_points = list(self.state.curve_points)
        snapshot.mapping_curve_points = list(self.state.mapping_curve_points)
        revision = self._revision
        worker = FunctionWorker(prepare_recovery_snapshot, snapshot)
        self._autosave_worker = worker
        worker.signals.finished.connect(lambda result, token=revision: self._autosave_finished(token, result))
        worker.signals.failed.connect(self._autosave_failed)
        self.thread_pool.start(worker)

    def _autosave_finished(self, revision: int, result) -> None:
        self._autosave_worker = None
        temporary, target = result
        try:
            if revision == self._revision and self.state.dirty:
                temporary.replace(target)
                self.statusBar().showMessage(f"Recovery snapshot saved: {target.name}")
        except OSError as error:
            self.statusBar().showMessage(f"Autosave unavailable: {error}")
        finally:
            temporary.unlink(missing_ok=True)

    def _autosave_failed(self, message: str) -> None:
        self._autosave_worker = None
        self.statusBar().showMessage(f"Autosave unavailable: {message}")

    def _offer_recovery(self) -> None:
        snapshots = find_recovery_snapshots()
        if not snapshots:
            return
        snapshot = snapshots[0]
        choice = QMessageBox.question(
            self,
            "Recover Project",
            f"A recovery snapshot was found:\n{snapshot.name}\n\nOpen it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        try:
            load_project(snapshot, self.state)
            self._revision += 1
            self.image_panel.cancel_pending_load()
            self._invalidate_heightfield()
            self.viewport.clear_heightfield()
            self.state.project_path = None
            self.state.dirty = True
            self._recovery_snapshot = snapshot
            self.image_panel.refresh_from_state()
            self.terrain_panel.sync_from_state()
            self.history.reset(self.state, clean=False)
            self._update_history_actions()
            # Adjustment completion triggers heightfield generation in order.
            self.setWindowTitle("ClayField — Recovered *")
        except ProjectIOError as error:
            self._show_error(f"Recovery failed: {error}")

    def _remember_project(self, path) -> None:
        if path is None:
            return
        recent = [str(path)] + [item for item in self._settings.value("recent_projects", [], list) if item != str(path)]
        self._settings.setValue("recent_projects", recent[:10])

    def _populate_recent(self) -> None:
        self.recent_menu.clear()
        recent = self._settings.value("recent_projects", [], list)
        if not recent:
            self.recent_menu.addAction("No recent projects").setEnabled(False)
        for path in recent:
            action = self.recent_menu.addAction(path)
            action.triggered.connect(lambda checked=False, selected=path: self._open_project_path(selected))

    def _choose_surface_color(self) -> None:
        current = QColor.fromRgbF(*self.viewport.surface_color)
        color = QColorDialog.getColor(current, self, "Terrain Color")
        if color.isValid():
            self.viewport.surface_color = (color.redF(), color.greenF(), color.blueF())
            self.viewport.update()

    def _set_dark_theme(self, enabled: bool) -> None:
        apply_theme(enabled)
        self._settings.setValue("dark_theme", enabled)

    def _set_gpu_preview(self, enabled: bool) -> None:
        self.viewport.gpu_adjustments_enabled = enabled
        if not enabled:
            self.viewport.cancel_gpu_request()

    def _gpu_preview_failed(self, message: str) -> None:
        self.gpu_preview_action.setChecked(False)
        self.statusBar().showMessage(message, 10_000)

    def _choose_light_direction(self) -> None:
        angle, accepted = QInputDialog.getDouble(self, "Lighting Direction", "Azimuth (degrees)", self.viewport.light_azimuth, -180.0, 180.0, 1)
        if accepted:
            self.viewport.light_azimuth = angle
            self.viewport.update()

    def _show_cross_section(self) -> None:
        if self.state.physical_heightfield is None:
            self.statusBar().showMessage("Wait for the terrain preview to finish")
            return
        CrossSectionDialog(self.state.physical_heightfield, self.state.terrain_width_mm, self.state.terrain_depth_mm, self).exec()

    def _cancel_current_operation(self) -> None:
        if self._active_worker is not None:
            self._active_worker.cancel()
            self.statusBar().showMessage("Cancellation requested…")
        else:
            self.statusBar().showMessage("No cancellable operation is running")

    def _camera_view(self, view: str) -> None:
        self.viewport.set_camera_view(view, self.state.terrain_width_mm, self.state.terrain_depth_mm, self.state.maximum_height_mm)

    def _image_loaded(self, path: str) -> None:
        self._invalidate_heightfield()
        self.viewport.clear_heightfield()
        self.terrain_panel.update_aspect_ratio()
        self._camera_view("fit")
        self.history.reset(self.state, clean=False)
        self._update_history_actions()
        self._mark_dirty()
        self.statusBar().showMessage(f"Loaded image: {path}")

    def _mark_dirty(self) -> None:
        self._revision += 1
        self.history.record(self.state)
        self.state.dirty = True
        self._update_history_actions()
        self._update_title()

    def _update_title(self) -> None:
        project_name = self.state.project_path.name if self.state.project_path else "Untitled"
        self.setWindowTitle(f"ClayField — {project_name}{' *' if self.state.dirty else ''}")

    def _update_history_actions(self) -> None:
        self.undo_action.setEnabled(self.history.index > 0)
        self.redo_action.setEnabled(self.history.index + 1 < len(self.history.entries))

    def _apply_history(self, snapshot) -> None:
        if snapshot is None:
            return
        self._revision += 1
        restore_parameters(self.state, snapshot)
        self.state.dirty = self.history.is_dirty
        self.terrain_panel.sync_from_state()
        self.image_panel.refresh_from_state()
        if self.state.source_type != "image":
            self._rebuild_procedural_heightfield()
        self._update_history_actions()
        self._update_title()

    def _undo(self) -> None:
        self._apply_history(self.history.undo())

    def _redo(self) -> None:
        self._apply_history(self.history.redo())

    def _save_preset(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Preset", "clayfield-preset.json", "ClayField presets (*.json)")
        if not path:
            return
        try:
            output = save_preset(self.state, path)
            self.history.finish_group()
            self.statusBar().showMessage(f"Saved preset: {output}")
        except PresetError as error:
            self._show_error(str(error))

    def _load_preset(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Preset", "", "ClayField presets (*.json)")
        if not path:
            return
        try:
            snapshot = load_preset(path, self.state)
            self.history.finish_group()
            restore_parameters(self.state, snapshot)
            self.terrain_panel.sync_from_state()
            if self.state.source_image is not None and self.state.lock_aspect_ratio:
                self.terrain_panel.update_aspect_ratio()
            self._mark_dirty()
            self.history.finish_group()
            self.image_panel.refresh_from_state()
            if self.state.source_type != "image":
                self._rebuild_procedural_heightfield()
            self.statusBar().showMessage(f"Loaded preset: {path}")
        except PresetError as error:
            self._show_error(str(error))

    def _confirm_project_change(self) -> bool:
        if not self.state.dirty:
            return True
        choice = QMessageBox.question(
            self,
            "Unsaved Changes",
            "Save changes before switching projects?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if choice == QMessageBox.StandardButton.Save:
            previous_dirty = self.state.dirty
            self._save_project()
            return not self.state.dirty and previous_dirty
        if choice == QMessageBox.StandardButton.Discard:
            discard_recovery_snapshot(self.state.project_path)
            self._discard_recovered_snapshot()
            return True
        return False

    def _discard_recovered_snapshot(self) -> None:
        if self._recovery_snapshot is not None:
            self._recovery_snapshot.unlink(missing_ok=True)
            self._recovery_snapshot = None

    def closeEvent(self, event) -> None:
        if self._confirm_project_change():
            self._revision += 1
            self._autosave_timer.stop()
            event.accept()
        else:
            event.ignore()

    def _show_error(self, message: str) -> None:
        """Show processing failures visibly while retaining status context."""
        self.statusBar().showMessage(message, 10_000)
        QMessageBox.critical(self, "ClayField operation failed", message)
