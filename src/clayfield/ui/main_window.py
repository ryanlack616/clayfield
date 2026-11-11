"""Main ClayField application window."""

from __future__ import annotations

from copy import copy, deepcopy
from pathlib import Path

import numpy as np
from PySide6.QtCore import QSettings, QThreadPool, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
)

from clayfield.app.history import PARAMETER_EDIT, SCULPT_EDIT, EditLedger, ParameterHistory, restore_parameters
from clayfield.app.presets import PresetError, load_preset, save_preset
from clayfield.app.project_io import ProjectIOError, load_project, save_project
from clayfield.app.project_state import ProjectState
from clayfield.app.recovery import discard_recovery_snapshot, find_recovery_snapshots, prepare_recovery_snapshot
from clayfield.app.worker import FunctionWorker
from clayfield.export.tasks import (
    analyze_image_export_task,
    analyze_procedural_export_task,
    export_heightmap_task,
    export_mesh_task,
    export_procedural_heightmap_task,
    export_procedural_mesh_task,
)
from clayfield.field.model import FieldMetadata, NormalizedField
from clayfield.field.persistence import PipelineSnapshot, SourceDescriptor
from clayfield.field.processing import FieldProcessingSettings
from clayfield.field.workflow import evaluate_serialized_pipeline
from clayfield.geometry.container import ContainerSettings
from clayfield.sculpt.history import SculptHistory, apply_stroke
from clayfield.sculpt.session import SculptSession
from clayfield.terrain.fabrication import FabricationProfile, analyze_heightfield
from clayfield.terrain.heightfield import (
    PhysicalDimensions,
    generate_physical_heightfield,
    options_from_state,
    physical_height_bounds,
)
from clayfield.terrain.mapping import MappingSettings
from clayfield.ui.cross_section import CrossSectionDialog
from clayfield.ui.export_preview import ExportPreviewDialog
from clayfield.ui.height_colors import HeightColorDialog
from clayfield.ui.image_panel import ImagePanel
from clayfield.ui.sculpt_panel import SculptPanel
from clayfield.ui.terrain_panel import TerrainPanel
from clayfield.ui.theme import apply_theme
from clayfield.ui.viewport import Viewport


def _generate_heightfield_with_bounds(*args, **kwargs):
    """Generate a heightfield and compute preview bounds in the worker.

    The GUI thread only needs the min/max for normalization and the terrain
    readout; computing them here keeps the full-resolution scan off the UI
    thread for large fabrication resolutions.
    """
    heightfield = generate_physical_heightfield(*args, **kwargs)
    return heightfield, float(heightfield.min()), float(heightfield.max())


class MainWindow(QMainWindow):
    """Compose the image, terrain, and OpenGL viewport panels."""

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.state = ProjectState()
        self.history = ParameterHistory(self.state)
        # Sculpt strokes keep their own stack. Parameter snapshots never include the
        # heightfield, so mixing the two in one stack would restore geometry the user
        # never edited. The Edit menu consults this stack first.
        self.sculpt_history = SculptHistory()
        self.sculpt_session: SculptSession | None = None
        # The parameter stack and the sculpt stack store different data, so the
        # ledger records the order of their actions. Undo and redo then walk the
        # stack that owns the most recent edit instead of guessing from depth.
        self._ledger = EditLedger()
        # ``state.sculpt_offsets`` compared against this copy decides whether the
        # document is dirty when no parameter changed. It is refreshed on save and
        # on load, so undoing a parameter change cannot mark saved sculpt work as
        # clean or vice versa.
        self._sculpt_clean: np.ndarray | None = None
        self.thread_pool = QThreadPool.globalInstance()
        self._heightfield_generation = 0
        self._heightfield_workers = {}
        self._heightfield_key = None
        self._heightfield_image = None
        self._procedural_key = None
        self._external_field_cache = None
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
        self.viewport.initialization_failed.connect(
            lambda message: QTimer.singleShot(0, lambda: self._show_error(message))
        )
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
        # A scroll area's minimum width is small, so the splitter will squeeze a
        # sidebar narrower than its own layout needs. That produced a horizontal
        # scrollbar across the bottom of both panels, clipping the widest
        # controls by a few pixels. Holding each scroll area at its content's
        # hint keeps the splitter from shrinking below it, so the panels never
        # scroll sideways.
        for scroll, panel in ((image_scroll, self.image_panel), (terrain_scroll, self.terrain_panel)):
            scroll.setMinimumWidth(panel.sizeHint().width())
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
        close.clicked.connect(lambda: self.image_panel.set_compose_expanded(False))
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

        self.sculpt_panel = SculptPanel(self.viewport)
        self.sculpt_panel.sculpt_toggled.connect(self._set_sculpt_enabled)
        self.sculpt_panel.settings_changed.connect(self._sculpt_settings_changed)
        self.sculpt_panel.closed.connect(lambda: self._set_sculpt_panel_visible(False))
        self.viewport.sculpt_pressed.connect(self._sculpt_pressed)
        self.viewport.sculpt_moved.connect(self._sculpt_moved)
        self.viewport.sculpt_released.connect(self._sculpt_released)
        # The brush controls start hidden: a fresh launch has no geometry to
        # sculpt and a 250 px card parked over the canvas covers a fifth of the
        # viewport before the user has done anything. The View menu is the entry
        # point and arms the brush when it opens the panel.
        self.sculpt_panel.hide()
        # A parent's resizeEvent runs before its children are laid out, so the
        # viewport reports its own size once that size is final. Without this the
        # bottom-anchored brush panel keeps the position it had before the resize.
        self.viewport.resized.connect(self._position_canvas_overlays)
        self._position_canvas_overlays()

    def _set_sculpt_enabled(self, enabled: bool) -> None:
        """Route the brush mode through the panel and the viewport.

        The panel's combo and the View menu are two views of the same state, so
        the change is mirrored into both without re-emitting either signal.
        """
        enabled = bool(enabled)
        self.sculpt_panel.set_enabled(enabled)
        self.viewport.set_sculpt_mode(enabled)

    def _set_sculpt_panel_visible(self, visible: bool) -> None:
        """Show or hide the brush overlay.

        Opening the panel arms the brush and hiding it disarms, so one gesture
        from the View menu is enough to start sculpting. The panel's own combo
        can still disarm while the panel stays open, which is how a user parks
        the brush without losing the settings.
        """
        visible = bool(visible)
        # isHidden() reports the explicit show/hide flag; isVisible() also goes
        # false while an ancestor is hidden, which would skip the update.
        if self.sculpt_panel.isHidden() == visible:
            self.sculpt_panel.setVisible(visible)
        if self.sculpt_action.isChecked() != visible:
            self.sculpt_action.blockSignals(True)
            self.sculpt_action.setChecked(visible)
            self.sculpt_action.blockSignals(False)
        if not visible:
            self._set_sculpt_enabled(False)
        elif not self.sculpt_panel.enabled:
            self._set_sculpt_enabled(True)
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
            self.compose_overlay.move(
                max(margin, self.viewport.width() - self.compose_overlay.width() - margin), margin
            )
        if hasattr(self, "sculpt_panel"):
            # Anchor the brush controls to the bottom-left corner so they never
            # cover the preview or compose overlays in the top corners. The
            # panel's height comes from its layout, which runs after the parent's
            # resize event, so settle the size before measuring the bottom edge.
            self.sculpt_panel.adjustSize()
            self.sculpt_panel.move(margin, max(margin, self.viewport.height() - self.sculpt_panel.height() - margin))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_canvas_overlays()

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        for label, callback in (
            ("New Project", self._new_project),
            ("Open Project", self._open_project),
            ("Save Project", self._save_project),
            ("Save Project As…", self._save_project_as),
            ("Export STL", self._export_stl),
            ("Export 3MF", self._export_3mf),
            ("Export Heightmap", self._export_heightmap),
            ("Exit", self.close),
        ):
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
        for label, view in (
            ("Reset Camera", "reset"),
            ("Fit Terrain", "fit"),
            ("Top View", "top"),
            ("Front View", "front"),
            ("Side View", "side"),
            ("Isometric View", "isometric"),
        ):
            action = view_menu.addAction(label)
            action.triggered.connect(lambda checked=False, selected=view: self._camera_view(selected))
        wireframe = view_menu.addAction("Wireframe")
        wireframe.setCheckable(True)
        wireframe.toggled.connect(self.viewport.set_wireframe)
        orthographic = view_menu.addAction("Orthographic Projection")
        orthographic.setCheckable(True)
        orthographic.toggled.connect(self.viewport.set_orthographic)
        self.grid_action = view_menu.addAction("Show Grid")
        self.grid_action.setCheckable(True)
        # Both check marks read the viewport's starting state instead of
        # hardcoding one, so the menu cannot contradict what paintGL draws.
        self.grid_action.setChecked(self.viewport.show_grid)
        self.grid_action.toggled.connect(self.viewport.set_grid_visible)
        # The theme comes from the saved settings, so the check mark has to match
        # the palette that __init__ already applied instead of assuming dark.
        self.dark_theme_action = view_menu.addAction("Dark Theme")
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.setChecked(bool(self._settings.value("dark_theme", False, type=bool)))
        self.dark_theme_action.toggled.connect(self._set_dark_theme)
        self.height_coloring_action = view_menu.addAction("Height Coloring")
        self.height_coloring_action.setCheckable(True)
        self.height_coloring_action.setChecked(self.viewport.height_coloring)
        self.height_coloring_action.setToolTip("Colour the surface by elevation instead of a flat colour")
        self.height_coloring_action.toggled.connect(self.viewport.set_height_coloring)
        height_colors = view_menu.addAction("Height Colors…")
        height_colors.setToolTip("Choose the low and high colours of the height ramp")
        height_colors.triggered.connect(self._choose_height_colors)
        self.gpu_preview_action = view_menu.addAction("GPU Image Preview")
        self.gpu_preview_action.setCheckable(True)
        self.gpu_preview_action.setChecked(True)
        self.gpu_preview_action.toggled.connect(self._set_gpu_preview)
        self.sculpt_action = view_menu.addAction("Sculpt Brush")
        self.sculpt_action.setCheckable(True)
        # Unchecked to match the panel, which _build_canvas_overlays leaves
        # hidden on launch. Set before the connection so no toggle fires here.
        self.sculpt_action.setChecked(False)
        self.sculpt_action.setShortcut("Ctrl+B")
        self.sculpt_action.setToolTip("Show the sculpt brush controls and route left-drag to the brush")
        self.sculpt_action.toggled.connect(self._set_sculpt_panel_visible)
        color = view_menu.addAction("Surface Color…")
        color.triggered.connect(self._choose_surface_color)
        light = view_menu.addAction("Lighting Direction…")
        light.triggered.connect(self._choose_light_direction)
        cross_section = view_menu.addAction("Cross-section…")
        cross_section.triggered.connect(self._show_cross_section)
        # Composition used to be a section toggle at the bottom of the left
        # panel. The menu is now its only entry point, so the control stays
        # discoverable without occupying a row in the scroll area.
        compose = view_menu.addAction("Compose…")
        compose.setToolTip("Show the secondary field and mask controls")
        compose.triggered.connect(lambda: self.image_panel.set_compose_expanded(True))
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
                    self._reset_edit_history(clean=True)
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
        self._reset_edit_history(clean=True, discard_sculpt=True)
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
            self._reset_edit_history(clean=True)
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
            path, _ = QFileDialog.getSaveFileName(
                self, "Save ClayField Project", "project.clayfield", "ClayField projects (*.clayfield)"
            )
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
        # The saved sculpt layer becomes the reference for the dirty comparison.
        self._remember_sculpt_clean()
        self._update_history_actions()
        self._remember_project(output)
        discard_recovery_snapshot(previous_path)
        if previous_path != output:
            discard_recovery_snapshot(output)
        self._discard_recovered_snapshot()
        self.setWindowTitle(f"ClayField — {output.name}")
        self.statusBar().showMessage(f"Saved project: {output}")

    def _rebuild_heightfield(self) -> None:
        if (
            self.state.source_type == "image"
            and self.state.composition_settings.get("enabled")
            and self.state.secondary_source_descriptor is not None
        ):
            self._rebuild_composed_image_heightfield()
            return
        if self.state.source_type != "image":
            self._rebuild_procedural_heightfield()
            return
        image = self.state.adjusted_image
        if image is None:
            return
        state = self.state
        key = (
            state.terrain_width_mm,
            state.terrain_depth_mm,
            state.minimum_height_mm,
            state.maximum_height_mm,
            state.heightfield_resolution,
            state.height_invert,
            state.smoothing_sigma,
            state.edge_falloff,
            state.height_mapping_gamma,
            state.noise_amplitude,
            state.noise_frequency,
            state.noise_seed,
            tuple(state.mapping_curve_points),
            state.edge_falloff_mode,
            state.relief_mode,
            options_from_state(state),
        )
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
        secondary = (
            SourceDescriptor.from_dict(self.state.secondary_source_descriptor)
            if self.state.secondary_source_descriptor is not None
            else None
        )
        mask = (
            SourceDescriptor.from_dict(self.state.mask_source_descriptor)
            if self.state.mask_source_descriptor is not None
            else None
        )
        snapshot = PipelineSnapshot.from_settings(
            descriptor,
            processing,
            secondary_processing=FieldProcessingSettings(**self.state.secondary_processing_settings)
            if self.state.secondary_processing_settings
            else None,
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
            # The adjusted image is already float32 and dedicated to this
            # heightfield pass; wrap it without a second full-image copy.
            primary = NormalizedField(
                np.asarray(image, dtype=np.float32), FieldMetadata("image", "adjusted_image", "1"), copy=False
            )
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
        worker.signals.progress.connect(
            lambda percent, message: self.statusBar().showMessage(f"Image composition: {percent}% — {message}")
        )
        worker.signals.finished.connect(lambda result, generation=token: self._procedural_finished(generation, result))
        worker.signals.failed.connect(lambda message, generation=token: self._procedural_failed(generation, message))
        worker.signals.cancelled.connect(lambda generation=token: self._heightfield_workers.pop(generation, None))
        self.thread_pool.start(worker)

    def _external_fields(self) -> dict[str, NormalizedField]:
        """Return cached normalized wrappers for the external fields.

        ``NormalizedField`` copies its input by default, so rebuilding the
        wrappers on every heightfield/export call would copy each external field
        repeatedly. Both external arrays are already read-only when they reach
        the state, so the wrappers use ``copy=False`` and share the array rather
        than allocating a second full-size copy. The cache key uses object
        identity plus the stored content hash: replacing either field or its
        descriptor invalidates the entry.
        """
        secondary = self.state.secondary_field
        mask = self.state.mask_field
        secondary_descriptor = self.state.secondary_source_descriptor
        mask_descriptor = self.state.mask_source_descriptor
        key = (
            id(secondary),
            id(mask),
            secondary_descriptor.get("content_hash") if secondary_descriptor else None,
            mask_descriptor.get("content_hash") if mask_descriptor else None,
        )
        cached = self._external_field_cache
        if cached is not None and cached[0] == key:
            return cached[1]
        fields: dict[str, NormalizedField] = {}
        for values, descriptor_data in ((secondary, secondary_descriptor), (mask, mask_descriptor)):
            if values is None or descriptor_data is None:
                continue
            descriptor = SourceDescriptor.from_dict(descriptor_data)
            if descriptor.content_hash is not None:
                fields[descriptor.content_hash] = NormalizedField(
                    np.asarray(values, dtype=np.float32),
                    FieldMetadata("external", "embedded_field", "1"),
                    copy=False,
                )
        # Keep strong references to the source arrays alongside the cache entry.
        # The key uses id(), and without a reference the array can be collected
        # and its address reused by a different array that happens to carry the
        # same descriptor hash, which would return a stale field.
        self._external_field_cache = (key, fields, secondary, mask)
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
            dimensions = PhysicalDimensions(
                self.state.terrain_width_mm,
                self.state.terrain_depth_mm,
                self.state.minimum_height_mm,
                self.state.maximum_height_mm,
            )
            return (
                analyze_image_export_task,
                (
                    self.state.adjusted_image,
                    dimensions,
                    self.state.export_resolution,
                    self.state.base_thickness_mm,
                    self.state.relief_mode,
                    self.state.smoothing_sigma,
                    self.state.edge_falloff,
                    self.state.height_invert,
                    self.state.height_mapping_gamma,
                    self.state.noise_amplitude,
                    self.state.noise_frequency,
                    self.state.noise_seed,
                    list(self.state.mapping_curve_points),
                    self.state.edge_falloff_mode,
                ),
                {
                    "height_options": options_from_state(self.state),
                    "profile": FabricationProfile(**self.state.fabrication_profile),
                },
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
            # Wrap the adjusted image without a second full-image copy. The
            # field contract still marks the array read-only.
            primary = NormalizedField(
                np.asarray(self.state.adjusted_image, dtype=np.float32),
                FieldMetadata("image", "adjusted_image", "1"),
                copy=False,
            )
        return (
            analyze_procedural_export_task,
            (
                snapshot,
                self.state.export_resolution,
                self.state.terrain_width_mm,
                self.state.terrain_depth_mm,
                self.state.base_thickness_mm,
                self.state.relief_mode,
            ),
            {
                "external_fields": self._external_fields(),
                "primary_field": primary,
                "profile": FabricationProfile(**self.state.fabrication_profile),
            },
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
        worker = FunctionWorker(
            evaluate_serialized_pipeline,
            snapshot,
            (resolution[1], resolution[0]),
            external_fields=self._external_fields(),
            inject_control=True,
        )
        self._heightfield_workers[token] = worker
        worker.signals.progress.connect(
            lambda percent, message: self.statusBar().showMessage(f"Procedural field: {percent}% — {message}")
        )
        worker.signals.finished.connect(lambda result, generation=token: self._procedural_finished(generation, result))
        worker.signals.failed.connect(lambda message, generation=token: self._procedural_failed(generation, message))
        worker.signals.cancelled.connect(lambda generation=token: self._heightfield_workers.pop(generation, None))
        self.thread_pool.start(worker)

    def _procedural_finished(self, generation: int, result) -> None:
        self._heightfield_workers.pop(generation, None)
        if generation != self._heightfield_generation:
            return
        base = result.physical_heightfield
        final = self._apply_sculpt_layer(base)
        self.state.physical_heightfield = final
        self.image_panel.set_procedural_preview(result.normalized_field.values)
        final_min, final_max = float(final.min()), float(final.max())
        if self.state.relief_mode == "negative":
            display = -final
            display_min, display_max = -final_max, -final_min
        else:
            display = final
            display_min, display_max = final_min, final_max
        self.viewport.set_height_range(display_min, display_max)
        self.viewport.set_heightfield(display, self.state.terrain_width_mm, self.state.terrain_depth_mm)
        self.image_panel.set_heightfield_preview(display, bounds=(display_min, display_max))
        self.terrain_panel.set_actual_height_range(display_min, display_max)
        self.terrain_panel.set_fabrication_metrics(
            analyze_heightfield(
                display,
                self.state.terrain_width_mm,
                self.state.terrain_depth_mm,
                self.state.base_thickness_mm,
                "positive",
                profile=FabricationProfile(**self.state.fabrication_profile),
            )
        )
        self.statusBar().showMessage("Procedural field ready")

    def _procedural_failed(self, generation: int, message: str) -> None:
        self._heightfield_workers.pop(generation, None)
        if generation == self._heightfield_generation:
            self._show_error(f"Procedural field failed: {message}")

    def _gpu_preview_ready(self, generation: int, image) -> None:
        if (
            image is None
            or generation != self.image_panel._adjustment_generation
            or self.state.adjusted_image is not None
        ):
            return
        self._heightfield_generation += 1
        self._start_heightfield_worker(image, self._heightfield_generation, provisional=True)

    def _request_gpu_adjustments(self, generation, image, settings, points) -> None:
        state = self.state
        if (
            state.smoothing_sigma
            or state.noise_amplitude
            or state.edge_falloff
            or state.height_invert
            or state.height_normalize
            or state.height_clamp_min != 0
            or state.height_clamp_max != 1
        ):
            return
        if state.maximum_height_mm < state.minimum_height_mm:
            return
        dimensions = PhysicalDimensions(
            state.terrain_width_mm, state.terrain_depth_mm, state.minimum_height_mm, state.maximum_height_mm
        )
        minimum, maximum = physical_height_bounds(dimensions, options_from_state(state))
        terrain = {
            "width": state.terrain_width_mm,
            "depth": state.terrain_depth_mm,
            "minimum": minimum,
            "maximum": maximum,
            "resolution": state.heightfield_resolution,
            "gamma": state.height_mapping_gamma,
            "curve": list(state.mapping_curve_points),
            "sign": -1.0 if state.relief_mode == "negative" else 1.0,
        }
        self.viewport.request_gpu_adjustments(generation, image, settings, points, terrain)

    def _start_heightfield_worker(self, image, token: int, provisional: bool) -> None:
        dimensions = PhysicalDimensions(
            self.state.terrain_width_mm,
            self.state.terrain_depth_mm,
            self.state.minimum_height_mm,
            self.state.maximum_height_mm,
        )
        options = options_from_state(self.state)
        resolution = self.state.heightfield_resolution
        if resolution is None and min(image.shape[:2]) < 2:
            resolution = (max(2, image.shape[1]), max(2, image.shape[0]))
        worker = FunctionWorker(
            _generate_heightfield_with_bounds,
            image,
            dimensions,
            resolution,
            self.state.height_invert,
            self.state.smoothing_sigma,
            self.state.edge_falloff,
            self.state.height_mapping_gamma,
            self.state.noise_amplitude,
            self.state.noise_frequency,
            self.state.noise_seed,
            list(self.state.mapping_curve_points),
            self.state.edge_falloff_mode,
            options=options,
        )
        self._heightfield_workers[token] = worker
        worker.signals.finished.connect(
            lambda result, generation=token, dims=dimensions, mode=self.state.relief_mode, preview=provisional, opts=options: (
                self._heightfield_finished(generation, dims, result, mode, preview, opts)
            )
        )
        worker.signals.failed.connect(lambda message, generation=token: self._heightfield_failed(generation, message))
        self.thread_pool.start(worker)

    def _invalidate_heightfield(self) -> None:
        self._heightfield_generation += 1
        self._heightfield_key = None
        self._heightfield_image = None
        self._procedural_key = None
        self.state.physical_heightfield = None
        self.image_panel.clear_adjustment_cache()
        self.image_panel.set_heightfield_preview(None)

    def _heightfield_finished(
        self,
        generation: int,
        dimensions: PhysicalDimensions,
        result,
        mode: str = "positive",
        provisional: bool = False,
        options=None,
    ) -> None:
        self._heightfield_workers.pop(generation, None)
        if generation != self._heightfield_generation:
            return
        heightfield, worker_min, worker_max = result
        if not provisional:
            heightfield = self._apply_sculpt_layer(heightfield)
            self.state.physical_heightfield = heightfield
        if mode == "negative":
            display = -heightfield
            display_min, display_max = -worker_max, -worker_min
        else:
            display = heightfield
            display_min, display_max = worker_min, worker_max
        low, high = physical_height_bounds(dimensions, options or options_from_state(self.state))
        minimum, maximum = (-high, -low) if mode == "negative" else (low, high)
        if not provisional:
            # The sculpt layer can raise or lower the extremes beyond the base
            # field's worker bounds, so the final display range is measured here.
            display_min, display_max = float(display.min()), float(display.max())
            if display_max > display_min:
                self.viewport.set_height_range(display_min, display_max)
        elif maximum > minimum:
            self.viewport.set_height_range(minimum, maximum)
        self.viewport.set_heightfield(display, dimensions.width_mm, dimensions.depth_mm)
        if not provisional:
            self.image_panel.set_heightfield_preview(display, bounds=(display_min, display_max))
            self.terrain_panel.set_actual_height_range(display_min, display_max)
            self.terrain_panel.set_fabrication_metrics(
                analyze_heightfield(
                    display,
                    dimensions.width_mm,
                    dimensions.depth_mm,
                    self.state.base_thickness_mm,
                    "positive",
                    profile=FabricationProfile(**self.state.fabrication_profile),
                )
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
        if (
            ExportPreviewDialog(self.state, label, self, final_analysis=self._final_export_analysis()).exec()
            != QDialog.DialogCode.Accepted
        ):
            return
        path, _ = QFileDialog.getSaveFileName(self, f"Export {label}", default_name, file_filter)
        if not path:
            return
        extension = ".stl" if file_type == "stl" else ".3mf"
        if Path(path).suffix.lower() != extension:
            path += extension
        dimensions = PhysicalDimensions(
            self.state.terrain_width_mm,
            self.state.terrain_depth_mm,
            self.state.minimum_height_mm,
            self.state.maximum_height_mm,
        )
        self._export_active = True
        self.export_progress.setValue(0)
        self.export_progress.show()
        if procedural:
            worker = FunctionWorker(
                export_procedural_mesh_task,
                self._procedural_snapshot(),
                dimensions,
                self.state.export_resolution,
                self.state.base_thickness_mm,
                self.state.relief_mode,
                path,
                file_type,
                external_fields=self._external_fields(),
                container_settings=self._container_settings(),
                inject_control=True,
            )
        else:
            worker = FunctionWorker(
                export_mesh_task,
                image,
                dimensions,
                self.state.export_resolution,
                self.state.base_thickness_mm,
                self.state.relief_mode,
                path,
                file_type,
                self.state.smoothing_sigma,
                self.state.edge_falloff,
                self.state.height_invert,
                self.state.height_mapping_gamma,
                self.state.noise_amplitude,
                self.state.noise_frequency,
                self.state.noise_seed,
                list(self.state.mapping_curve_points),
                self.state.edge_falloff_mode,
                height_options=options_from_state(self.state),
                container_settings=self._container_settings(),
                inject_control=True,
            )
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
        if (
            ExportPreviewDialog(
                self.state, "Heightmap", self, mesh=False, final_analysis=self._final_export_analysis()
            ).exec()
            != QDialog.DialogCode.Accepted
        ):
            return
        path, selected = QFileDialog.getSaveFileName(
            self,
            "Export Heightmap",
            "heightmap.png",
            "PNG 16-bit (*.png);;PNG 8-bit (*.png);;TIFF 16-bit (*.tif *.tiff);;TIFF 8-bit (*.tif *.tiff)",
        )
        if not path:
            return
        if not Path(path).suffix:
            path += ".tif" if selected.startswith("TIFF") else ".png"
        dimensions = PhysicalDimensions(
            self.state.terrain_width_mm,
            self.state.terrain_depth_mm,
            self.state.minimum_height_mm,
            self.state.maximum_height_mm,
        )
        self._export_active = True
        self.export_progress.setValue(0)
        self.export_progress.show()
        bit_depth = 8 if "8-bit" in selected else 16
        if procedural:
            worker = FunctionWorker(
                export_procedural_heightmap_task,
                self._procedural_snapshot(),
                self.state.export_resolution,
                path,
                bit_depth,
                external_fields=self._external_fields(),
                relief_mode=self.state.relief_mode,
                inject_control=True,
            )
        else:
            worker = FunctionWorker(
                export_heightmap_task,
                image,
                dimensions,
                self.state.export_resolution,
                path,
                bit_depth,
                self.state.smoothing_sigma,
                self.state.edge_falloff,
                self.state.height_invert,
                self.state.height_mapping_gamma,
                self.state.noise_amplitude,
                self.state.noise_frequency,
                self.state.noise_seed,
                list(self.state.mapping_curve_points),
                self.state.edge_falloff_mode,
                relief_mode=self.state.relief_mode,
                height_options=options_from_state(self.state),
                inject_control=True,
            )
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
            self._reset_edit_history(clean=False)
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
        """Pick the flat terrain colour.

        The flat colour is invisible while the height ramp is on, so accepting a
        colour switches back to it. Picking a colour is a request to see it, and
        the height ramp does the mirror image when it is chosen.
        """
        current = QColor.fromRgbF(*self.viewport.surface_color)
        color = QColorDialog.getColor(current, self, "Terrain Color")
        if color.isValid():
            self.viewport.surface_color = (color.redF(), color.greenF(), color.blueF())
            if self.height_coloring_action.isChecked():
                self.height_coloring_action.setChecked(False)
            self.viewport.update()

    def _set_dark_theme(self, enabled: bool) -> None:
        enabled = bool(enabled)
        apply_theme(enabled)
        self._settings.setValue("dark_theme", enabled)
        if self.dark_theme_action.isChecked() != enabled:
            # Programmatic theme changes must not re-enter through the action.
            self.dark_theme_action.blockSignals(True)
            self.dark_theme_action.setChecked(enabled)
            self.dark_theme_action.blockSignals(False)

    def _set_gpu_preview(self, enabled: bool) -> None:
        self.viewport.gpu_adjustments_enabled = enabled
        if not enabled:
            self.viewport.cancel_gpu_request()

    def _gpu_preview_failed(self, message: str) -> None:
        self.gpu_preview_action.setChecked(False)
        self.statusBar().showMessage(message, 10_000)

    def _choose_height_colors(self) -> None:
        """Edit the two ends of the height ramp."""
        dialog = HeightColorDialog(self.viewport.height_low_color, self.viewport.height_high_color, self)
        if dialog.exec():
            low, high = dialog.colors()
            self.viewport.set_height_colors(low, high)
            # Choosing a ramp is a request to see it, even if height colouring
            # was switched off earlier.
            if not self.height_coloring_action.isChecked():
                self.height_coloring_action.setChecked(True)

    def _choose_light_direction(self) -> None:
        angle, accepted = QInputDialog.getDouble(
            self, "Lighting Direction", "Azimuth (degrees)", self.viewport.light_azimuth, -180.0, 180.0, 1
        )
        if accepted:
            self.viewport.light_azimuth = angle
            self.viewport.update()

    def _show_cross_section(self) -> None:
        if self.state.physical_heightfield is None:
            self.statusBar().showMessage("Wait for the terrain preview to finish")
            return
        CrossSectionDialog(
            self.state.physical_heightfield, self.state.terrain_width_mm, self.state.terrain_depth_mm, self
        ).exec()

    def _cancel_current_operation(self) -> None:
        if self._active_worker is not None:
            self._active_worker.cancel()
            self.statusBar().showMessage("Cancellation requested…")
        else:
            self.statusBar().showMessage("No cancellable operation is running")

    def _camera_view(self, view: str) -> None:
        self.viewport.set_camera_view(
            view, self.state.terrain_width_mm, self.state.terrain_depth_mm, self.state.maximum_height_mm
        )

    def _image_loaded(self, path: str) -> None:
        self._invalidate_heightfield()
        self.viewport.clear_heightfield()
        self.terrain_panel.update_aspect_ratio()
        self._camera_view("fit")
        # A new image replaces the geometry the sculpt layer was painted on, so
        # the layer and its strokes are discarded rather than applied to it.
        self._reset_edit_history(clean=False, discard_sculpt=True)
        self._update_history_actions()
        self._mark_dirty()
        self.statusBar().showMessage(f"Loaded image: {path}")

    def _mark_dirty(self) -> None:
        self._revision += 1
        previous_index = self.history.index
        previous_length = len(self.history.entries)
        self.history.record(self.state)
        if self.history.index != previous_index:
            # A merged slider change updates the existing snapshot in place, so
            # only a moved index is a new action for the undo ledger. A stack at
            # its limit also dropped its oldest snapshot, which the ledger mirrors.
            self._ledger.record(PARAMETER_EDIT)
            if len(self.history.entries) == previous_length:
                self._ledger.drop_oldest(PARAMETER_EDIT)
        self.state.dirty = True
        self._update_history_actions()
        self._update_title()

    def _mark_sculpt_dirty(self) -> None:
        """Flag the document dirty without recording a parameter snapshot."""
        self._revision += 1
        self.state.dirty = True
        self._update_history_actions()
        self._update_title()

    def _sculpt_changed(self) -> bool:
        """Return whether the sculpt layer differs from the last saved state.

        A stroke is undone by subtracting the same displacement it added, so a
        perfect round trip lands within float32 rounding rather than exactly on
        the saved values. The comparison allows that epsilon: 1e-5 mm is ten
        nanometres, far below anything the viewport or an export can resolve, so
        a difference that small means the document was not really edited.
        """
        offsets = self.state.sculpt_offsets
        if offsets is None:
            return False
        if self._sculpt_clean is None:
            return True
        if offsets.shape != self._sculpt_clean.shape:
            return True
        if np.array_equal(offsets, self._sculpt_clean):
            return False
        return not bool(np.allclose(offsets, self._sculpt_clean, rtol=0.0, atol=1e-5))

    def _remember_sculpt_clean(self) -> None:
        """Snapshot the sculpt layer as the saved state."""
        offsets = self.state.sculpt_offsets
        self._sculpt_clean = None if offsets is None else offsets.copy()

    def _reset_edit_history(self, *, clean: bool, discard_sculpt: bool = False) -> None:
        """Reset the edit stacks after the document's source or project changes.

        ``discard_sculpt`` drops the sculpt layer as well. It is used when the
        geometry source is replaced, so a layer painted on the previous surface is
        never applied to unrelated geometry. Otherwise the layer survives and is
        remembered as the saved state.
        """
        self.history.reset(self.state, clean=clean)
        self._ledger.clear()
        if discard_sculpt:
            self._clear_sculpt_layer()
        else:
            self.sculpt_history.clear()
            self._remember_sculpt_clean()

    def _update_title(self) -> None:
        project_name = self.state.project_path.name if self.state.project_path else "Untitled"
        self.setWindowTitle(f"ClayField — {project_name}{' *' if self.state.dirty else ''}")

    def _update_history_actions(self) -> None:
        self.undo_action.setEnabled(self._ledger.can_undo)
        self.redo_action.setEnabled(self._ledger.can_redo)

    def _apply_sculpt_layer(self, base: np.ndarray) -> np.ndarray:
        """Return ``base + sculpt_offsets`` when a compatible layer exists.

        The layer is preserved across regenerations only when the grid shape still
        matches. A resolution or topology change discards it explicitly and reports
        the decision rather than silently applying offsets to unrelated geometry.
        """
        offsets = self.state.sculpt_offsets
        if offsets is None:
            self.state.sculpt_base = base
            return base
        if offsets.shape != base.shape:
            self._clear_sculpt_layer("Sculpt layer discarded: heightfield resolution changed")
            self.state.sculpt_base = base
            return base
        self.state.sculpt_base = base
        return base + offsets

    def _clear_sculpt_layer(self, message: str | None = None) -> None:
        """Drop the sculpt layer and its history."""
        self.state.sculpt_base = None
        self.state.sculpt_offsets = None
        self.sculpt_session = None
        self.sculpt_history.clear()
        self._sculpt_clean = None
        self._ledger.discard(SCULPT_EDIT)
        self._update_history_actions()
        if message:
            self.statusBar().showMessage(message)

    def _sculpt_settings_changed(self, settings) -> None:
        """Apply a brush change to the running stroke without restarting it."""
        self.viewport.set_brush_radius(settings.radius_mm)
        if self.sculpt_session is not None:
            self.sculpt_session.settings = settings

    def _sculpt_pressed(self, x_mm: float, z_mm: float) -> None:
        final = self.state.physical_heightfield
        if final is None:
            return
        offsets = self.state.sculpt_offsets
        base = self.state.sculpt_base
        if offsets is not None and (offsets.shape != final.shape or (base is not None and base.shape != final.shape)):
            # A layer from a different grid would either raise inside the session
            # or be applied to unrelated geometry. Drop it and start clean.
            self._clear_sculpt_layer("Sculpt layer discarded: heightfield shape changed")
        if self.state.sculpt_base is None or self.state.sculpt_offsets is None:
            # The base is the evaluated field before any sculpt. The displacement
            # layer starts at zero so ``final == base + offsets`` from the outset.
            self.state.sculpt_base = final.copy()
            self.state.sculpt_offsets = np.zeros_like(final)
        settings = self.sculpt_panel.settings()
        self.sculpt_session = SculptSession(
            final,
            self.state.sculpt_offsets,
            self.state.terrain_width_mm,
            self.state.terrain_depth_mm,
            settings,
            self.sculpt_history,
        )
        self.sculpt_session.begin_stroke(x_mm, z_mm)
        self._refresh_sculpt_display()

    def _sculpt_moved(self, x_mm: float, z_mm: float) -> None:
        if self.sculpt_session is None:
            return
        if self.sculpt_session.apply_stroke(x_mm, z_mm):
            self._refresh_sculpt_display()

    def _sculpt_released(self) -> None:
        if self.sculpt_session is None:
            return
        stroke = self.sculpt_session.finish()
        self.sculpt_session = None
        if stroke is not None:
            self._ledger.record(SCULPT_EDIT)
            self._mark_sculpt_dirty()

    def _refresh_sculpt_display(self) -> None:
        """Re-upload the evaluated heightfield after a brush dab.

        The viewport derives normals in its vertex shader from the height texture,
        so moving cells needs no separate normal buffer update. The upload is a
        decimated display texture rather than the full fabrication grid, which keeps
        a dab well inside interactive latency without a partial-texture path.
        """
        final = self.state.physical_heightfield
        if final is None:
            return
        display = -final if self.state.relief_mode == "negative" else final
        minimum, maximum = float(display.min()), float(display.max())
        if maximum > minimum:
            self.viewport.set_height_range(minimum, maximum)
        self.viewport.set_heightfield(display, self.state.terrain_width_mm, self.state.terrain_depth_mm)
        self.image_panel.set_heightfield_preview(display, bounds=(minimum, maximum))

    def _apply_history(self, snapshot) -> None:
        if snapshot is None:
            return
        self._revision += 1
        restore_parameters(self.state, snapshot)
        self.state.dirty = self.history.is_dirty or self._sculpt_changed()
        self.terrain_panel.sync_from_state()
        self.image_panel.refresh_from_state()
        if self.state.source_type != "image":
            self._rebuild_procedural_heightfield()
        self._update_history_actions()
        self._update_title()

    def _apply_sculpt_stroke(self, stroke, *, forward: bool) -> None:
        """Restore one stroke's before or after blocks and refresh the viewport."""
        heightfield = self.state.physical_heightfield
        offsets = self.state.sculpt_offsets
        if heightfield is None or offsets is None:
            return
        apply_stroke(heightfield, offsets, stroke, forward=forward)
        self._revision += 1
        # Undoing a stroke back to the saved layer leaves the document clean, so
        # the flag is recomputed rather than forced. A plain ``True`` here kept
        # the title marked dirty and asked to save an unchanged project.
        self.state.dirty = self._sculpt_changed() or self.history.is_dirty
        self._refresh_sculpt_display()
        self._update_history_actions()
        self._update_title()

    def _undo(self) -> None:
        """Undo the most recent parameter or sculpt action."""
        while True:
            kind = self._ledger.undo()
            if kind is None:
                return
            if kind == SCULPT_EDIT:
                if not self.sculpt_history.can_undo:
                    # The ledger outlived its stack; drop the stale actions and
                    # try the next one rather than doing nothing.
                    self._ledger.discard(SCULPT_EDIT)
                    continue
                stroke = self.sculpt_history.undo()
                if stroke is not None:
                    self._apply_sculpt_stroke(stroke, forward=False)
                return
            if self.history.index == 0:
                self._ledger.discard(PARAMETER_EDIT)
                continue
            snapshot = self.history.undo()
            if snapshot is not None:
                self._apply_history(snapshot)
            return

    def _redo(self) -> None:
        """Redo the most recently undone parameter or sculpt action."""
        while True:
            kind = self._ledger.redo()
            if kind is None:
                return
            if kind == SCULPT_EDIT:
                if not self.sculpt_history.can_redo:
                    self._ledger.discard(SCULPT_EDIT)
                    continue
                stroke = self.sculpt_history.redo()
                if stroke is not None:
                    self._apply_sculpt_stroke(stroke, forward=True)
                return
            if self.history.index + 1 >= len(self.history.entries):
                self._ledger.discard(PARAMETER_EDIT)
                continue
            snapshot = self.history.redo()
            if snapshot is not None:
                self._apply_history(snapshot)
            return

    def _save_preset(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Preset", "clayfield-preset.json", "ClayField presets (*.json)"
        )
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
