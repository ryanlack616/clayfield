"""Physical terrain controls for the first heightfield workflow."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from clayfield.app.project_state import ProjectState
from clayfield.geometry.estimates import estimate_solid_mesh
from clayfield.image.geometry import processed_dimensions
from clayfield.terrain.fabrication import FABRICATION_PROFILES, FabricationMetrics
from clayfield.terrain.heightfield import PhysicalDimensions, options_from_state, physical_height_bounds
from clayfield.ui.curve_editor import CurveEditor
from clayfield.ui.parameter_row import parameter_row


class TerrainPanel(QWidget):
    """Edit physical dimensions and heightfield resolution."""

    parameters_changed = Signal()

    def __init__(self, state: ProjectState, parent=None) -> None:
        super().__init__(parent)
        self.state = state
        self.width = self._dimension(100.0)
        self.width.setRange(0.01, 300.0)
        self.depth = self._dimension(100.0)
        self.depth.setRange(0.01, 300.0)
        self.minimum = self._dimension(0.0)
        self.minimum.setRange(0.0, 10.0)
        self.minimum.setValue(0.0)
        self.maximum = self._dimension(8.0)
        self.maximum.setRange(0.0, 20.0)
        self.base_thickness = self._dimension(5.0)
        self.mapping_gamma = QDoubleSpinBox()
        self.mapping_gamma.setRange(0.05, 10.0)
        self.mapping_gamma.setSingleStep(0.05)
        self.mapping_gamma.setValue(1.0)
        self.mapping_gamma.setToolTip("Independent intensity-to-height mapping gamma")
        self.height_invert = QCheckBox("Invert height mapping")
        self.height_normalize = QCheckBox("Normalize height input")
        self.height_offset = self._dimension(0.0)
        self.height_offset.setRange(-10.0, 10.0)
        self.height_offset.setValue(0.0)
        self.height_scale = QDoubleSpinBox()
        self.height_scale.setRange(0.0, 5.0)
        self.height_scale.setValue(1.0)
        self.height_scale.setSingleStep(0.1)
        self.height_clamp_min = QDoubleSpinBox()
        self.height_clamp_max = QDoubleSpinBox()
        for control in (self.height_clamp_min, self.height_clamp_max):
            control.setRange(0, 1)
            control.setSingleStep(0.05)
        self.height_clamp_max.setValue(1.0)
        self.lock_aspect = QCheckBox("Lock width/depth aspect ratio")
        self.lock_aspect.setChecked(True)
        self.noise_amplitude = QDoubleSpinBox()
        self.noise_amplitude.setRange(0.0, 1.0)
        self.noise_amplitude.setSingleStep(0.01)
        self.noise_frequency = QDoubleSpinBox()
        self.noise_frequency.setRange(0.1, 32.0)
        self.noise_frequency.setSingleStep(0.1)
        self.noise_frequency.setValue(1.0)
        self.noise_seed = QSpinBox()
        self.noise_seed.setRange(-2147483648, 2147483647)
        self.noise_octaves = QSpinBox()
        self.noise_octaves.setRange(1, 8)
        self.noise_persistence = QDoubleSpinBox()
        self.noise_persistence.setRange(0, 1)
        self.noise_persistence.setSingleStep(0.05)
        self.noise_persistence.setValue(0.5)
        self.mapping_curve = CurveEditor(self)
        self.mapping_curve.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.mapping_curve.setMinimumHeight(180)
        self.mapping_curve.curve_changed.connect(self._changed)
        self.smoothing = QDoubleSpinBox()
        self.smoothing.setRange(0.0, 50.0)
        self.smoothing.setSingleStep(0.1)
        self.smoothing.setSuffix(" px")
        self.smoothing_strength = QDoubleSpinBox()
        self.smoothing_strength.setRange(0, 1)
        self.smoothing_strength.setSingleStep(0.05)
        self.smoothing_strength.setValue(1.0)
        self.edge_falloff = QDoubleSpinBox()
        self.edge_falloff_mode = QComboBox()
        self.edge_falloff_mode.addItems(["Linear", "Smoothstep"])
        self.edge_falloff.setRange(0.0, 1.0)
        self.edge_falloff.setSingleStep(0.05)
        self.edge_falloff.setSuffix(" ratio")
        self.edge_strength = QDoubleSpinBox()
        self.edge_strength.setRange(0, 1)
        self.edge_strength.setSingleStep(0.05)
        self.edge_strength.setValue(1.0)
        self.relief_mode = QComboBox()
        self.relief_mode.addItems(["Positive", "Negative"])
        self.fabrication_profile = QComboBox()
        self.fabrication_profile.addItems(list(FABRICATION_PROFILES))
        self.container_mode = QComboBox()
        self.container_mode.addItems(["None", "Open-top tray"])
        self.container_wall = self._dimension(2.0)
        self.container_clearance = self._dimension(2.0)
        self.container_outside = QCheckBox("Use outside dimensions")
        self.container_outside.setChecked(True)
        self.container_outside.toggled.connect(self._changed)
        self.resolution = QSpinBox()
        self.resolution.setRange(32, 2048)
        self.resolution.setSingleStep(32)
        self.resolution.setValue(2048)
        self.export_resolution = QSpinBox()
        self.export_resolution.setRange(32, 4096)
        self.export_resolution.setSingleStep(32)
        self.export_resolution.setValue(2048)
        self.estimate = QLabel()
        self.estimate.setWordWrap(True)
        self.height_info = QLabel()
        self.height_info.setWordWrap(True)
        self.fabrication_info = QLabel()
        self.fabrication_info.setWordWrap(True)
        form = QFormLayout()
        for label, widget in (
            ("Width (mm)", self.width),
            ("Depth (mm)", self.depth),
            ("Minimum height (mm)", self.minimum),
            ("Maximum height (mm)", self.maximum),
            ("Height offset (mm)", self.height_offset),
            ("Height scale", self.height_scale),
            ("Height clamp minimum", self.height_clamp_min),
            ("Height clamp maximum", self.height_clamp_max),
            ("Height mapping gamma", self.mapping_gamma),
            ("Smoothing", self.smoothing),
            ("Smoothing strength", self.smoothing_strength),
            ("Edge falloff", self.edge_falloff),
            ("Falloff strength", self.edge_strength),
            ("Falloff mode", self.edge_falloff_mode),
            ("Relief mode", self.relief_mode),
            ("Preview resolution", self.resolution),
        ):
            form.addRow(
                label, parameter_row(widget, label) if isinstance(widget, (QSpinBox, QDoubleSpinBox)) else widget
            )
            if hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self._changed)
            elif hasattr(widget, "currentTextChanged"):
                widget.currentTextChanged.connect(self._changed)
        form_box = QWidget()
        form_box.setLayout(form)
        form.addRow(self.container_outside)
        curve_box = QWidget()
        curve_layout = QVBoxLayout(curve_box)
        curve_layout.setContentsMargins(0, 0, 0, 0)
        curve_layout.addWidget(QLabel("Height mapping curve"))
        curve_layout.addWidget(self.mapping_curve)
        curve_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        fabrication_form = QFormLayout()
        fabrication_form.addRow("Model thickness (mm)", parameter_row(self.base_thickness, "Model thickness"))
        fabrication_form.addRow("Fabrication profile", self.fabrication_profile)
        fabrication_form.addRow("Container", self.container_mode)
        fabrication_form.addRow("Wall thickness (mm)", parameter_row(self.container_wall, "Wall thickness"))
        fabrication_form.addRow(
            "Clearance above model (mm)", parameter_row(self.container_clearance, "Clearance above model")
        )
        fabrication_form.addRow("Export resolution", parameter_row(self.export_resolution, "Export resolution"))
        fabrication_box = QWidget()
        fabrication_box.setLayout(fabrication_form)
        self.container_mode.currentTextChanged.connect(self._update_container_controls)
        for widget in (
            self.base_thickness,
            self.container_wall,
            self.container_clearance,
            self.fabrication_profile,
            self.container_mode,
            self.export_resolution,
        ):
            if hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self._changed)
            else:
                widget.currentTextChanged.connect(self._changed)
        detail_toggle = QToolButton()
        detail_toggle.setObjectName("sectionButton")
        detail_toggle.setText("HEIGHT DETAILS  ▾")
        detail_toggle.setCheckable(True)
        detail_toggle.setChecked(True)
        detail_toggle.toggled.connect(
            lambda expanded: (
                form_box.setVisible(expanded),
                detail_toggle.setText("HEIGHT DETAILS  ▾" if expanded else "HEIGHT DETAILS  ▸"),
            )
        )
        analysis_box = QWidget()
        analysis_layout = QVBoxLayout(analysis_box)
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        analysis_layout.addWidget(self.estimate)
        analysis_layout.addWidget(self.height_info)
        analysis_layout.addWidget(self.fabrication_info)
        analysis_toggle = QToolButton()
        analysis_toggle.setObjectName("sectionButton")
        analysis_toggle.setText("ANALYSIS  ▾")
        analysis_toggle.setCheckable(True)
        analysis_toggle.setChecked(True)
        analysis_toggle.toggled.connect(
            lambda expanded: (
                analysis_box.setVisible(expanded),
                analysis_toggle.setText("ANALYSIS  ▾" if expanded else "ANALYSIS  ▸"),
            )
        )
        layout = QVBoxLayout(self)
        heading = QLabel("HEIGHT / FABRICATE")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        layout.addWidget(curve_box)
        layout.addWidget(self.lock_aspect)
        layout.addWidget(self.height_invert)
        layout.addWidget(self.height_normalize)
        reset = QPushButton("Reset Terrain")
        reset.setToolTip("Restore terrain dimensions, mapping, and modifiers to their defaults.")
        reset.clicked.connect(self.reset)
        layout.addWidget(detail_toggle)
        layout.addWidget(form_box)
        layout.addWidget(reset)
        fabrication_toggle = QToolButton()
        fabrication_toggle.setObjectName("sectionButton")
        fabrication_toggle.setText("FABRICATION / EXPORT  ▾")
        fabrication_toggle.setCheckable(True)
        fabrication_toggle.setChecked(True)
        fabrication_toggle.toggled.connect(
            lambda expanded: (
                fabrication_box.setVisible(expanded),
                fabrication_toggle.setText("FABRICATION / EXPORT  ▾" if expanded else "FABRICATION / EXPORT  ▸"),
            )
        )
        layout.addWidget(fabrication_toggle)
        layout.addWidget(fabrication_box)
        layout.addWidget(analysis_toggle)
        layout.addWidget(analysis_box)
        self.lock_aspect.stateChanged.connect(self._changed)
        self.height_invert.toggled.connect(self._changed)
        self.height_normalize.toggled.connect(self._changed)
        layout.addStretch()
        self._update_estimate()
        self._update_height_info()
        self.fabrication_info.setText("Fabrication analysis: waiting for a heightfield")
        self._update_container_controls(self.container_mode.currentText())

    def _update_container_controls(self, mode: str) -> None:
        """Only expose tray dimensions when a tray will be exported."""
        enabled = mode == "Open-top tray"
        self.container_wall.setEnabled(enabled)
        self.container_clearance.setEnabled(enabled)
        self.container_outside.setEnabled(enabled)

    @staticmethod
    def _dimension(value: float) -> QDoubleSpinBox:
        widget = QDoubleSpinBox()
        widget.setRange(0.01, 10000.0)
        widget.setDecimals(3)
        widget.setSingleStep(1.0)
        widget.setValue(value)
        return widget

    def sync_from_state(self) -> None:
        """Reflect loaded project terrain settings without losing them."""
        widgets = (
            (self.width, self.state.terrain_width_mm),
            (self.depth, self.state.terrain_depth_mm),
            (self.minimum, self.state.minimum_height_mm),
            (self.maximum, self.state.maximum_height_mm),
            (self.base_thickness, self.state.base_thickness_mm),
            (self.mapping_gamma, self.state.height_mapping_gamma),
            (self.noise_amplitude, self.state.noise_amplitude),
            (self.noise_frequency, self.state.noise_frequency),
            (self.noise_seed, self.state.noise_seed),
            (self.smoothing, self.state.smoothing_sigma),
            (self.edge_falloff, self.state.edge_falloff),
            (self.height_offset, self.state.height_offset_mm),
            (self.height_scale, self.state.height_scale),
            (self.height_clamp_min, self.state.height_clamp_min),
            (self.height_clamp_max, self.state.height_clamp_max),
            (self.smoothing_strength, self.state.smoothing_strength),
            (self.edge_strength, self.state.edge_falloff_strength),
            (self.noise_octaves, self.state.noise_octaves),
            (self.noise_persistence, self.state.noise_persistence),
        )
        for widget, value in widgets:
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)
        self.lock_aspect.blockSignals(True)
        self.lock_aspect.setChecked(self.state.lock_aspect_ratio)
        self.lock_aspect.blockSignals(False)
        for widget, value in (
            (self.height_invert, self.state.height_invert),
            (self.height_normalize, self.state.height_normalize),
        ):
            widget.blockSignals(True)
            widget.setChecked(value)
            widget.blockSignals(False)
        self.edge_falloff_mode.blockSignals(True)
        self.edge_falloff_mode.setCurrentText(
            "Smoothstep" if self.state.edge_falloff_mode == "smoothstep" else "Linear"
        )
        self.edge_falloff_mode.blockSignals(False)
        self.mapping_curve.points = list(self.state.mapping_curve_points)
        self.mapping_curve.update()
        self.relief_mode.blockSignals(True)
        self.relief_mode.setCurrentText("Negative" if self.state.relief_mode == "negative" else "Positive")
        self.relief_mode.blockSignals(False)
        self.fabrication_profile.blockSignals(True)
        self.fabrication_profile.setCurrentText(self.state.fabrication_profile.get("name", "Generic FDM"))
        self.fabrication_profile.blockSignals(False)
        self.container_mode.blockSignals(True)
        self.container_mode.setCurrentText("Open-top tray" if self.state.container_mode == "open_tray" else "None")
        self.container_mode.blockSignals(False)
        self._update_container_controls(self.container_mode.currentText())
        for widget, value in (
            (self.container_wall, self.state.container_wall_thickness_mm),
            (self.container_clearance, self.state.container_clearance_mm),
        ):
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)
        self.container_outside.blockSignals(True)
        self.container_outside.setChecked(self.state.container_outside_dimensions)
        self.container_outside.blockSignals(False)
        self.resolution.blockSignals(True)
        self.resolution.setValue(max(self.state.heightfield_resolution) if self.state.heightfield_resolution else 2048)
        self.resolution.blockSignals(False)
        self.export_resolution.blockSignals(True)
        self.export_resolution.setValue(max(self.state.export_resolution))
        self.export_resolution.blockSignals(False)
        self._update_estimate()
        self._update_height_info()

    def _update_estimate(self) -> None:
        preview_width, preview_height = self.state.heightfield_resolution or (
            self.resolution.value(),
            self.resolution.value(),
        )
        export_width, export_height = self.state.export_resolution
        estimate = estimate_solid_mesh(export_height, export_width)
        warning = (
            "\nWarning: large export; mesh generation may require substantial memory."
            if estimate.working_mebibytes >= 512.0
            else ""
        )
        self.estimate.setText(
            f"Preview samples: {preview_width} × {preview_height}\n"
            f"Export samples: {export_width} × {export_height}\n"
            f"Estimated solid: {estimate.vertex_count:,} vertices / {estimate.triangle_count:,} triangles\n"
            f"Mesh arrays: {estimate.total_mebibytes:.1f} MiB; working estimate: {estimate.working_mebibytes:.1f} MiB{warning}"
        )

    def _changed(self) -> None:
        if self.height_clamp_min.value() > self.height_clamp_max.value():
            other = self.height_clamp_max if self.sender() is self.height_clamp_min else self.height_clamp_min
            other.blockSignals(True)
            other.setValue(
                self.height_clamp_min.value() if other is self.height_clamp_max else self.height_clamp_max.value()
            )
            other.blockSignals(False)
        image_width, image_height = processed_dimensions(
            self.state.image_width, self.state.image_height, self.state.crop_margins, self.state.image_resize
        )
        if self.lock_aspect.isChecked() and self.state.image_width and self.state.image_height:
            ratio = image_height / image_width
            if self.sender() is self.depth:
                self.width.blockSignals(True)
                self.width.setValue(self.depth.value() / ratio)
                self.width.blockSignals(False)
            elif self.sender() in (self.width, self.lock_aspect):
                self.depth.blockSignals(True)
                self.depth.setValue(self.width.value() * ratio)
                self.depth.blockSignals(False)
        self.state.terrain_width_mm = self.width.value()
        self.state.terrain_depth_mm = self.depth.value()
        self.state.minimum_height_mm = self.minimum.value()
        self.state.maximum_height_mm = self.maximum.value()
        self.state.base_thickness_mm = self.base_thickness.value()
        self.state.height_mapping_gamma = self.mapping_gamma.value()
        self.state.noise_amplitude = self.noise_amplitude.value()
        self.state.noise_frequency = self.noise_frequency.value()
        self.state.noise_seed = self.noise_seed.value()
        self.state.noise_octaves = self.noise_octaves.value()
        self.state.noise_persistence = self.noise_persistence.value()
        self.state.height_invert = self.height_invert.isChecked()
        self.state.height_normalize = self.height_normalize.isChecked()
        self.state.height_offset_mm = self.height_offset.value()
        self.state.height_scale = self.height_scale.value()
        self.state.height_clamp_min = self.height_clamp_min.value()
        self.state.height_clamp_max = self.height_clamp_max.value()
        self.state.smoothing_strength = self.smoothing_strength.value()
        self.state.edge_falloff_strength = self.edge_strength.value()
        self.state.mapping_curve_points = list(self.mapping_curve.points)
        self.state.lock_aspect_ratio = self.lock_aspect.isChecked()
        self.state.smoothing_sigma = self.smoothing.value()
        self.state.edge_falloff = self.edge_falloff.value()
        self.state.edge_falloff_mode = (
            "smoothstep" if self.edge_falloff_mode.currentText() == "Smoothstep" else "linear"
        )
        self.state.relief_mode = "negative" if self.relief_mode.currentText() == "Negative" else "positive"
        self.state.fabrication_profile = dict(FABRICATION_PROFILES[self.fabrication_profile.currentText()].__dict__)
        self.state.container_mode = "open_tray" if self.container_mode.currentText() == "Open-top tray" else "none"
        self.state.container_wall_thickness_mm = self.container_wall.value()
        self.state.container_clearance_mm = self.container_clearance.value()
        self.state.container_outside_dimensions = self.container_outside.isChecked()
        size = self.resolution.value()
        aspect = (
            image_height / image_width
            if image_width and image_height
            else self.state.terrain_depth_mm / max(self.state.terrain_width_mm, 0.01)
        )
        resolution_aspect = aspect if self.state.lock_aspect_ratio or self.state.source_type != "image" else 1.0
        preview_width = max(2, round(size / max(1.0, resolution_aspect)))
        preview_height = max(2, round(size * min(1.0, resolution_aspect)))
        self.state.heightfield_resolution = (preview_width, preview_height)
        export_size = self.export_resolution.value()
        export_width = max(2, round(export_size / max(1.0, resolution_aspect)))
        export_height = max(2, round(export_size * min(1.0, resolution_aspect)))
        self.state.export_resolution = (export_width, export_height)
        self._update_estimate()
        self._update_height_info()
        self.state.dirty = True
        self.parameters_changed.emit()

    def update_aspect_ratio(self) -> None:
        """Update dimensions and sample counts for a newly loaded image."""
        if self.lock_aspect.isChecked() and self.state.image_width and self.state.image_height:
            width, height = processed_dimensions(
                self.state.image_width, self.state.image_height, self.state.crop_margins, self.state.image_resize
            )
            self.depth.blockSignals(True)
            self.depth.setValue(self.width.value() * height / width)
            self.depth.blockSignals(False)
        self._changed()

    def _update_height_info(self) -> None:
        dimensions = PhysicalDimensions(
            self.state.terrain_width_mm,
            self.state.terrain_depth_mm,
            self.state.minimum_height_mm,
            self.state.maximum_height_mm,
        )
        low, high = physical_height_bounds(dimensions, options_from_state(self.state))
        wall = (
            self.state.base_thickness_mm - high
            if self.state.relief_mode == "negative"
            else self.state.base_thickness_mm + low
        )
        warning = " — insufficient base thickness" if wall <= 0 else ""
        self.height_info.setText(
            f"Mapped height: {low:.2f}–{high:.2f} mm\nEstimated minimum wall: {wall:.2f} mm{warning}"
        )

    def set_actual_height_range(self, low: float, high: float) -> None:
        wall = self.state.base_thickness_mm + low
        warning = " — insufficient base thickness" if wall <= 0 else ""
        self.height_info.setText(f"Actual surface: {low:.2f}–{high:.2f} mm\nMinimum wall: {wall:.2f} mm{warning}")

    def set_fabrication_metrics(self, metrics: FabricationMetrics) -> None:
        warnings = ", ".join(metrics.warnings) if metrics.warnings else "none"
        self.fabrication_info.setText(
            f"Resolved feature estimate: {metrics.minimum_resolved_feature_width_mm:.3f} mm\n"
            f"Maximum slope: {metrics.maximum_slope_degrees:.1f}°\n"
            f"High-frequency ratio: {metrics.high_frequency_ratio:.3f}\n"
            f"Warnings: {warnings}"
        )

    def reset(self) -> None:
        """Reset terrain controls without changing the source or image adjustments."""
        defaults = ProjectState()
        names = (
            "terrain_width_mm",
            "terrain_depth_mm",
            "minimum_height_mm",
            "maximum_height_mm",
            "base_thickness_mm",
            "height_mapping_gamma",
            "noise_amplitude",
            "noise_frequency",
            "noise_seed",
            "noise_octaves",
            "noise_persistence",
            "height_invert",
            "height_normalize",
            "height_offset_mm",
            "height_scale",
            "height_clamp_min",
            "height_clamp_max",
            "smoothing_sigma",
            "smoothing_strength",
            "edge_falloff",
            "edge_falloff_strength",
            "edge_falloff_mode",
            "relief_mode",
            "lock_aspect_ratio",
            "heightfield_resolution",
            "export_resolution",
            "mapping_curve_points",
        )
        for name in names:
            setattr(self.state, name, getattr(defaults, name))
        self.sync_from_state()
        self.update_aspect_ratio()
