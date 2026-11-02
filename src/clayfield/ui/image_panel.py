"""Image loading and basic display controls."""

from __future__ import annotations

from pathlib import Path
import hashlib

import cv2
import numpy as np
from PySide6.QtCore import QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QFileDialog, QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLayout, QLineEdit, QPushButton, QSizePolicy, QSpinBox, QStackedWidget, QToolButton, QVBoxLayout, QWidget

from clayfield.app.project_state import ProjectState
from clayfield.app.worker import FunctionWorker
from clayfield.image.grayscale import to_grayscale
from clayfield.image.pipeline import AdjustmentCache
from clayfield.app.cancellation import check_cancelled
from clayfield.ui.curve_editor import CurveEditor
from clayfield.ui.histogram import HistogramWidget
from clayfield.ui.parameter_row import parameter_row
from clayfield.image.loader import load_image
from clayfield.image.geometry import apply_image_geometry
from clayfield.field.generators import MandelbrotParameters, NoiseParameters, WaveParameters
from clayfield.field.persistence import SourceDescriptor


def _load_and_convert(path: str, linear_light: bool):
    loaded = load_image(path)
    grayscale = to_grayscale(loaded.pixels, linear_light=linear_light)
    return loaded, grayscale, linear_light


def _load_external_field(path: str):
    loaded = load_image(path)
    field = to_grayscale(loaded.pixels)
    original = Path(path).read_bytes()
    return field, loaded.path.name, hashlib.sha256(original).hexdigest(), original


def _process_adjustments(source, grayscale, settings, points, cache, margins, resize, *, cancel_check=None, progress_callback=None):
    check_cancelled(cancel_check)
    if grayscale is None:
        pixels = apply_image_geometry(source, margins, resize)
        grayscale = to_grayscale(pixels, linear_light=bool(settings.get("linear_light", False)))
    check_cancelled(cancel_check)
    return grayscale, cache.apply(grayscale, settings, points, cancel_check=cancel_check)


class ImagePanel(QWidget):
    """Own image controls while writing authoritative values to ProjectState."""

    error_occurred = Signal(str)
    image_loaded = Signal(str)
    parameters_changed = Signal()
    processing_started = Signal()
    adjusted_image_ready = Signal()
    gpu_adjustment_requested = Signal(int, object, object, object)
    image_geometry_changed = Signal()
    procedural_source_changed = Signal()
    composition_requested = Signal(bool)
    preview_availability_changed = Signal(bool)

    def __init__(self, state: ProjectState, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.state = state
        self.thread_pool = QThreadPool(self)
        self._adjustment_generation = 0
        self._adjustment_workers = {}
        self._adjustment_cache = AdjustmentCache()
        self._pending_adjustments = None
        self._adjustment_timer = QTimer(self)
        self._adjustment_timer.setSingleShot(True)
        self._adjustment_timer.setInterval(40)
        self._adjustment_timer.timeout.connect(self._launch_adjustments)
        self._load_generation = 0
        self._load_workers = {}
        self.preview = QLabel("No image loaded")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(180)
        self.preview.setWordWrap(True)
        self.preview_mode = QComboBox()
        self.preview_mode.addItems(["Adjusted image", "Original image", "Final heightmap"])
        self.preview_mode.currentIndexChanged.connect(self._refresh_preview)
        self._heightfield_preview = None
        self._procedural_preview = None
        self.info = QLabel("Load a PNG, JPEG, TIFF, or BMP image.")
        self.histogram = HistogramWidget(self)
        self.histogram.markers_changed.connect(self._histogram_markers_changed)
        self.curve_editor = CurveEditor(self)
        self.curve_editor.curve_changed.connect(self._refresh_adjustments)
        self.info.setWordWrap(True)
        self.load_button = QPushButton("Load Image…")
        self.source_mode = QComboBox()
        self.source_mode.addItems(["Image", "Fractal noise", "Wave interference", "Mandelbrot", "Voronoi", "Ridged noise", "Warped noise", "SDF shapes", "Chladni", "Spectral", "Reaction-diffusion", "Phyllotaxis", "Cellular automata", "Flow field", "Erosion", "L-system", "Cracks", "Penrose", "Truchet", "Superformula", "Gaussian peaks", "Julia", "Moiré", "Gabor", "QFractalNow config"])
        self.source_mode.currentIndexChanged.connect(self._source_mode_changed)
        self.source_randomize = QPushButton("Randomize Source")
        self.source_reset = QPushButton("Reset Source")
        self.source_randomize.clicked.connect(self._randomize_source)
        self.source_reset.clicked.connect(self._reset_source)
        self.source_mode.setToolTip("Choose an image or deterministic mathematical pattern source")
        self.procedural_stack = QStackedWidget()
        self.procedural_controls = self._build_procedural_controls()
        self.composition_controls = self._build_composition_controls()
        self.compose_toggle = QToolButton()
        self.compose_toggle.setObjectName("sectionButton")
        self.compose_toggle.setText("COMPOSE  ▸")
        self.compose_toggle.setCheckable(True)
        self.compose_toggle.setChecked(False)
        self.compose_toggle.toggled.connect(self._toggle_compose)
        self.external_status = QLabel("Import a generated heightmap or mask")
        self.provenance = QLabel()
        self.provenance.setWordWrap(True)
        self._external_import_worker = None
        self._external_import_generation = 0
        self.grayscale_button = QPushButton("Grayscale")
        self.invert_button = QPushButton("Invert")
        self.controls = {}
        self.threshold_enabled = QCheckBox("Enable threshold")
        self.linear_light = QCheckBox("Linear-light grayscale")
        self.linear_light.setToolTip("Convert sRGB channels to linear light before luminance weighting")
        self.linear_light.stateChanged.connect(self._apply_grayscale)
        self.curve_interpolation = QComboBox()
        self.curve_interpolation.addItems(["Linear", "Smoothstep"])
        self.curve_interpolation.currentTextChanged.connect(self._refresh_adjustments)
        self.threshold_enabled.stateChanged.connect(self._refresh_adjustments)
        self.reset_button = QPushButton("Reset Adjustments")
        self.reset_button.clicked.connect(self._reset_adjustments)
        self.crop_controls = []
        for _ in range(4):
            control = QSpinBox()
            control.setRange(0, 99)
            control.setSuffix(" %")
            control.valueChanged.connect(self._geometry_changed)
            self.crop_controls.append(control)
        self.resize_enabled = QCheckBox("Resize source")
        self.resize_width = QSpinBox()
        self.resize_height = QSpinBox()
        for control in (self.resize_width, self.resize_height):
            control.setRange(2, 8192)
            control.setValue(512)
            control.setSuffix(" px")
            control.valueChanged.connect(self._geometry_changed)
        self.resize_enabled.toggled.connect(self._geometry_changed)
        for name, value, minimum, maximum, step in (
            ("Black point", 0.0, 0.0, 0.99, 0.01),
            ("Gamma", 1.0, 0.1, 5.0, 0.05),
            ("White point", 1.0, 0.01, 1.0, 0.01),
            ("Output black", 0.0, 0.0, 1.0, 0.01),
            ("Output white", 1.0, 0.0, 1.0, 0.01),
            ("Brightness", 0.0, -1.0, 1.0, 0.01),
            ("Contrast", 1.0, 0.0, 4.0, 0.05),
            ("Blur", 0.0, 0.0, 20.0, 0.1),
            ("Sharpen", 0.0, 0.0, 5.0, 0.1),
            ("Threshold", 0.5, 0.0, 1.0, 0.01),
        ):
            control = QDoubleSpinBox()
            control.setRange(minimum, maximum)
            control.setSingleStep(step)
            control.setValue(value)
            control.valueChanged.connect(self._refresh_adjustments)
            self.controls[name] = control
        self.grayscale_button.setEnabled(False)
        self.invert_button.setEnabled(False)
        self.load_button.clicked.connect(self._choose_image)
        self.grayscale_button.clicked.connect(self._apply_grayscale)
        self.invert_button.clicked.connect(self._apply_invert)
        def section(title: str, content: QWidget, expanded: bool = True) -> tuple[QToolButton, QWidget]:
            toggle = QToolButton()
            toggle.setText(f"{title}  ▾" if expanded else f"{title}  ▸")
            toggle.setCheckable(True)
            toggle.setChecked(expanded)
            content.setVisible(expanded)
            toggle.toggled.connect(lambda visible, label=title: (content.setVisible(visible), toggle.setText(f"{label}  ▾" if visible else f"{label}  ▸")))
            return toggle, content

        source_content = QWidget()
        self.source_content = source_content
        source_content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        source_layout = QVBoxLayout(source_content)
        source_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.addWidget(QLabel("Primary source"))
        source_layout.addWidget(self.source_mode)
        source_layout.addWidget(self.load_button)
        source_actions = QHBoxLayout()
        source_actions.setContentsMargins(0, 0, 0, 0)
        source_actions.addWidget(self.source_randomize)
        source_actions.addWidget(self.source_reset)
        source_layout.addLayout(source_actions)
        source_layout.addWidget(self.procedural_stack)
        source_layout.addWidget(self.info)
        source_layout.addWidget(self.provenance)
        self.procedural_stack.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        process_content = QWidget()
        process_layout = QVBoxLayout(process_content)
        process_layout.setContentsMargins(0, 0, 0, 0)
        process_layout.addWidget(self.preview_mode)
        process_layout.addWidget(self.histogram)
        process_layout.addWidget(self.curve_editor)
        process_actions = QHBoxLayout()
        process_actions.setContentsMargins(0, 0, 0, 0)
        process_actions.addWidget(self.grayscale_button)
        process_actions.addWidget(self.invert_button)
        process_layout.addLayout(process_actions)
        process_layout.addWidget(self.threshold_enabled)
        process_layout.addWidget(self.reset_button)
        process_layout.addWidget(self.linear_light)
        process_layout.addWidget(QLabel("Curve interpolation"))
        process_layout.addWidget(self.curve_interpolation)
        form = QFormLayout()
        for name, control in self.controls.items():
            form.addRow(name, parameter_row(control, name))
        process_layout.addLayout(form)

        source_toggle, source_content = section("SOURCE", source_content)
        process_toggle, process_content = section("PROCESS", process_content)
        process_toggle.setObjectName("sectionButton")
        layout = QVBoxLayout(self)
        layout.addWidget(source_content)
        layout.addWidget(process_toggle)
        layout.addWidget(process_content)
        layout.addStretch()
        layout.addWidget(self.compose_toggle)
        for name, widget in {"source_mode": self.source_mode, "source_randomize": self.source_randomize, "source_reset": self.source_reset, **self.procedural_controls, **self.composition_controls}.items():
            if isinstance(widget, QWidget):
                widget.setAccessibleName(name.replace("_", " ").title())
        self.composition_controls["enabled"].setToolTip("Enable a second field before composition")
        self.composition_controls["operation"].setToolTip("Choose how the secondary field combines with the primary field")
        self.composition_controls["amount"].setToolTip("How strongly the composition replaces the primary field")
        self._source_mode_changed(0)
        self._toggle_compose(False)
        self._update_provenance()

    def _toggle_compose(self, expanded: bool) -> None:
        self.composition_controls["box"].setVisible(bool(expanded))
        self.compose_toggle.setText("COMPOSE  ▾" if expanded else "COMPOSE  ▸")
        self.composition_requested.emit(bool(expanded))
        self._update_provenance()

    def _update_provenance(self) -> None:
        primary = self.state.source_type
        secondary = self.state.secondary_source_descriptor or {}
        mask = self.state.mask_source_descriptor or {}
        lines = []
        if secondary:
            lines.append(f"Secondary: {secondary.get('type', 'unknown')} ({'embedded' if self.state.secondary_field is not None else 'external'})")
        if mask:
            lines.append(f"Mask: {mask.get('type', 'unknown')} ({'embedded' if self.state.mask_field is not None else 'external'})")
        if self.state.pipeline_snapshot and self.state.pipeline_snapshot.get("algorithm_versions"):
            versions = self.state.pipeline_snapshot["algorithm_versions"]
            lines.append("Pipeline algorithms: " + ", ".join(f"{key} {value}" for key, value in sorted(versions.items())))
        self.provenance.setText("\n".join(lines))

    def _build_procedural_controls(self) -> dict[str, object]:
        """Build compact source controls without coupling them to generation."""
        controls: dict[str, object] = {}
        noise_page = QWidget()
        noise_form = QFormLayout(noise_page)
        controls["noise_seed"] = QSpinBox(); controls["noise_seed"].setRange(-2147483648, 2147483647)
        controls["noise_frequency"] = QDoubleSpinBox(); controls["noise_frequency"].setRange(0.1, 64.0); controls["noise_frequency"].setValue(2.0); controls["noise_frequency"].setSingleStep(0.1)
        controls["noise_octaves"] = QSpinBox(); controls["noise_octaves"].setRange(1, 12); controls["noise_octaves"].setValue(6)
        controls["noise_persistence"] = QDoubleSpinBox(); controls["noise_persistence"].setRange(0.0, 1.0); controls["noise_persistence"].setValue(0.5); controls["noise_persistence"].setSingleStep(0.05)
        controls["noise_lacunarity"] = QDoubleSpinBox(); controls["noise_lacunarity"].setRange(0.1, 8.0); controls["noise_lacunarity"].setValue(2.0); controls["noise_lacunarity"].setSingleStep(0.1)
        controls["noise_amplitude"] = QDoubleSpinBox(); controls["noise_amplitude"].setRange(0.0, 1.0); controls["noise_amplitude"].setValue(1.0); controls["noise_amplitude"].setSingleStep(0.05)
        controls["noise_normalization"] = QComboBox(); controls["noise_normalization"].addItems(["Auto", "Fixed"])
        controls["noise_tileable"] = QCheckBox("Tileable (integer frequencies only)")
        for label, name in (("Seed", "noise_seed"), ("Base frequency", "noise_frequency"), ("Octaves", "noise_octaves"), ("Persistence", "noise_persistence"), ("Lacunarity", "noise_lacunarity"), ("Amplitude", "noise_amplitude"), ("Normalization", "noise_normalization")):
            noise_form.addRow(label, controls[name])
        noise_form.addRow(controls["noise_tileable"])

        wave_page = QWidget()
        wave_form = QFormLayout(wave_page)
        controls["wave_mode"] = QComboBox(); controls["wave_mode"].addItems(["Planar", "Radial"])
        controls["wave_frequency_x"] = QDoubleSpinBox(); controls["wave_frequency_x"].setRange(0.1, 64.0); controls["wave_frequency_x"].setValue(3.0)
        controls["wave_frequency_y"] = QDoubleSpinBox(); controls["wave_frequency_y"].setRange(0.1, 64.0); controls["wave_frequency_y"].setValue(3.0)
        controls["wave_amplitude_x"] = QDoubleSpinBox(); controls["wave_amplitude_x"].setRange(-1.0, 1.0); controls["wave_amplitude_x"].setValue(1.0); controls["wave_amplitude_x"].setSingleStep(0.05)
        controls["wave_amplitude_y"] = QDoubleSpinBox(); controls["wave_amplitude_y"].setRange(-1.0, 1.0); controls["wave_amplitude_y"].setValue(1.0); controls["wave_amplitude_y"].setSingleStep(0.05)
        controls["wave_output_amplitude"] = QDoubleSpinBox(); controls["wave_output_amplitude"].setRange(0.0, 1.0); controls["wave_output_amplitude"].setValue(1.0); controls["wave_output_amplitude"].setSingleStep(0.05)
        for label, name in (("Mode", "wave_mode"), ("Frequency X", "wave_frequency_x"), ("Frequency Y", "wave_frequency_y"), ("Amplitude X", "wave_amplitude_x"), ("Amplitude Y", "wave_amplitude_y"), ("Output amplitude", "wave_output_amplitude")):
            wave_form.addRow(label, controls[name])

        mandelbrot_page = QWidget()
        mandelbrot_form = QFormLayout(mandelbrot_page)
        controls["mandelbrot_center_real"] = QDoubleSpinBox(); controls["mandelbrot_center_real"].setRange(-2.0, 2.0); controls["mandelbrot_center_real"].setValue(-0.5); controls["mandelbrot_center_real"].setSingleStep(0.05)
        controls["mandelbrot_center_imaginary"] = QDoubleSpinBox(); controls["mandelbrot_center_imaginary"].setRange(-2.0, 2.0); controls["mandelbrot_center_imaginary"].setValue(0.0); controls["mandelbrot_center_imaginary"].setSingleStep(0.05)
        controls["mandelbrot_zoom"] = QDoubleSpinBox(); controls["mandelbrot_zoom"].setRange(0.1, 1000.0); controls["mandelbrot_zoom"].setValue(1.0); controls["mandelbrot_zoom"].setSingleStep(0.1)
        controls["mandelbrot_iterations"] = QSpinBox(); controls["mandelbrot_iterations"].setRange(1, 2000); controls["mandelbrot_iterations"].setValue(100)
        controls["mandelbrot_contrast"] = QDoubleSpinBox(); controls["mandelbrot_contrast"].setRange(0.1, 10.0); controls["mandelbrot_contrast"].setValue(1.0); controls["mandelbrot_contrast"].setSingleStep(0.1)
        controls["mandelbrot_invert"] = QCheckBox("Invert escape field")
        for label, name in (("Center real", "mandelbrot_center_real"), ("Center imaginary", "mandelbrot_center_imaginary"), ("Zoom", "mandelbrot_zoom"), ("Iterations", "mandelbrot_iterations"), ("Contrast", "mandelbrot_contrast")):
            mandelbrot_form.addRow(label, controls[name])
        mandelbrot_form.addRow(controls["mandelbrot_invert"])

        voronoi_page = QWidget(); voronoi_form = QFormLayout(voronoi_page)
        controls["voronoi_seed"] = QSpinBox(); controls["voronoi_seed"].setRange(-2147483648, 2147483647)
        controls["voronoi_density"] = QDoubleSpinBox(); controls["voronoi_density"].setRange(1.0, 64.0); controls["voronoi_density"].setValue(8.0)
        controls["voronoi_jitter"] = QDoubleSpinBox(); controls["voronoi_jitter"].setRange(0.0, 1.0); controls["voronoi_jitter"].setValue(1.0); controls["voronoi_jitter"].setSingleStep(0.05)
        controls["voronoi_mode"] = QComboBox(); controls["voronoi_mode"].addItems(["Boundary", "Distance", "Cells"])
        for label, name in (("Seed", "voronoi_seed"), ("Cell density", "voronoi_density"), ("Jitter", "voronoi_jitter"), ("Mode", "voronoi_mode")):
            voronoi_form.addRow(label, controls[name])

        ridged_page = QWidget(); ridged_form = QFormLayout(ridged_page)
        controls["ridged_seed"] = QSpinBox(); controls["ridged_seed"].setRange(-2147483648, 2147483647)
        controls["ridged_frequency"] = QDoubleSpinBox(); controls["ridged_frequency"].setRange(0.1, 64.0); controls["ridged_frequency"].setValue(2.0)
        controls["ridged_octaves"] = QSpinBox(); controls["ridged_octaves"].setRange(1, 12); controls["ridged_octaves"].setValue(6)
        controls["ridged_sharpness"] = QDoubleSpinBox(); controls["ridged_sharpness"].setRange(0.1, 8.0); controls["ridged_sharpness"].setValue(2.0); controls["ridged_sharpness"].setSingleStep(0.1)
        for label, name in (("Seed", "ridged_seed"), ("Base frequency", "ridged_frequency"), ("Octaves", "ridged_octaves"), ("Sharpness", "ridged_sharpness")):
            ridged_form.addRow(label, controls[name])

        warped_page = QWidget(); warped_form = QFormLayout(warped_page)
        controls["warped_seed"] = QSpinBox(); controls["warped_seed"].setRange(-2147483648, 2147483647)
        controls["warped_frequency"] = QDoubleSpinBox(); controls["warped_frequency"].setRange(0.1, 64.0); controls["warped_frequency"].setValue(2.0)
        controls["warped_warp_frequency"] = QDoubleSpinBox(); controls["warped_warp_frequency"].setRange(0.1, 64.0); controls["warped_warp_frequency"].setValue(2.0)
        controls["warped_strength"] = QDoubleSpinBox(); controls["warped_strength"].setRange(0.0, 2.0); controls["warped_strength"].setValue(0.25); controls["warped_strength"].setSingleStep(0.05)
        controls["warped_octaves"] = QSpinBox(); controls["warped_octaves"].setRange(1, 12); controls["warped_octaves"].setValue(5)
        for label, name in (("Seed", "warped_seed"), ("Base frequency", "warped_frequency"), ("Warp frequency", "warped_warp_frequency"), ("Warp strength", "warped_strength"), ("Octaves", "warped_octaves")):
            warped_form.addRow(label, controls[name])

        sdf_page = QWidget(); sdf_form = QFormLayout(sdf_page)
        controls["sdf_shape"] = QComboBox(); controls["sdf_shape"].addItems(["Circle", "Rectangle"])
        controls["sdf_radius"] = QDoubleSpinBox(); controls["sdf_radius"].setRange(0.01, 1.0); controls["sdf_radius"].setValue(0.35); controls["sdf_radius"].setSingleStep(0.05)
        controls["sdf_width"] = QDoubleSpinBox(); controls["sdf_width"].setRange(0.01, 1.0); controls["sdf_width"].setValue(0.6)
        controls["sdf_height"] = QDoubleSpinBox(); controls["sdf_height"].setRange(0.01, 1.0); controls["sdf_height"].setValue(0.6)
        controls["sdf_repeats_x"] = QSpinBox(); controls["sdf_repeats_x"].setRange(1, 64)
        controls["sdf_repeats_y"] = QSpinBox(); controls["sdf_repeats_y"].setRange(1, 64)
        controls["sdf_softness"] = QDoubleSpinBox(); controls["sdf_softness"].setRange(0.001, 1.0); controls["sdf_softness"].setValue(0.05); controls["sdf_softness"].setSingleStep(0.01)
        controls["sdf_invert"] = QCheckBox("Invert shape")
        controls["sdf_boolean_shape"] = QComboBox(); controls["sdf_boolean_shape"].addItems(["None", "Circle", "Rectangle"])
        controls["sdf_boolean_operation"] = QComboBox(); controls["sdf_boolean_operation"].addItems(["Union", "Difference", "Intersection"])
        controls["sdf_boolean_offset_x"] = QDoubleSpinBox(); controls["sdf_boolean_offset_x"].setRange(-1.0, 1.0); controls["sdf_boolean_offset_x"].setSingleStep(0.05)
        controls["sdf_boolean_offset_y"] = QDoubleSpinBox(); controls["sdf_boolean_offset_y"].setRange(-1.0, 1.0); controls["sdf_boolean_offset_y"].setSingleStep(0.05)
        for label, name in (("Shape", "sdf_shape"), ("Radius", "sdf_radius"), ("Width", "sdf_width"), ("Height", "sdf_height"), ("Repeat X", "sdf_repeats_x"), ("Repeat Y", "sdf_repeats_y"), ("Edge softness", "sdf_softness")):
            sdf_form.addRow(label, controls[name])
        sdf_form.addRow(controls["sdf_invert"])
        for label, name in (("Boolean shape", "sdf_boolean_shape"), ("Boolean operation", "sdf_boolean_operation"), ("Boolean offset X", "sdf_boolean_offset_x"), ("Boolean offset Y", "sdf_boolean_offset_y")):
            sdf_form.addRow(label, controls[name])

        advanced_pages = []
        def advanced_page(title, specifications):
            page = QWidget(); form = QFormLayout(page)
            for name, kind, value, minimum, maximum in specifications:
                if kind == "int":
                    widget = QSpinBox(); widget.setRange(int(minimum), int(maximum)); widget.setValue(int(value))
                elif kind == "float":
                    widget = QDoubleSpinBox(); widget.setRange(float(minimum), float(maximum)); widget.setValue(float(value)); widget.setSingleStep(max(0.01, (float(maximum) - float(minimum)) / 100.0))
                elif kind == "check":
                    widget = QCheckBox()
                    widget.setChecked(bool(value))
                else:
                    widget = QDoubleSpinBox()
                controls[name] = widget
                form.addRow(name.replace("_", " ").title(), widget)
            advanced_pages.append(page)

        advanced_page("Chladni", [("chladni_mode_x", "int", 3, 1, 64), ("chladni_mode_y", "int", 5, 1, 64), ("chladni_phase", "float", 0.0, -6.28, 6.28), ("chladni_line_width", "float", 0.2, 0.01, 1.0)])
        advanced_page("Spectral", [("spectral_seed", "int", 0, -2147483648, 2147483647), ("spectral_components", "int", 12, 1, 128), ("spectral_min_frequency", "float", 1.0, 0.1, 64.0), ("spectral_max_frequency", "float", 12.0, 0.1, 128.0)])
        advanced_page("Reaction diffusion", [("reaction_seed", "int", 0, -2147483648, 2147483647), ("reaction_iterations", "int", 300, 1, 5000), ("reaction_feed", "float", 0.055, 0.0, 1.0), ("reaction_kill", "float", 0.062, 0.0, 1.0)])
        advanced_page("Phyllotaxis", [("phyllotaxis_count", "int", 500, 1, 10000), ("phyllotaxis_divergence", "float", 137.5, 0.0, 360.0), ("phyllotaxis_growth", "float", 0.018, 0.001, 1.0), ("phyllotaxis_radius", "float", 0.025, 0.001, 0.5)])
        advanced_page("Cellular automata", [("cellular_seed", "int", 0, -2147483648, 2147483647), ("cellular_iterations", "int", 10, 1, 100), ("cellular_density", "float", 0.45, 0.0, 1.0), ("cellular_birth", "int", 4, 0, 8), ("cellular_survival", "int", 4, 0, 8)])
        advanced_page("Flow field", [("flow_frequency", "float", 4.0, 0.1, 64.0), ("flow_swirl", "float", 1.0, 0.0, 8.0), ("flow_bands", "int", 8, 1, 128)])
        advanced_page("Erosion", [("erosion_seed", "int", 0, -2147483648, 2147483647), ("erosion_iterations", "int", 50, 1, 500), ("erosion_strength", "float", 0.25, 0.0, 1.0), ("erosion_evaporation", "float", 0.1, 0.0, 1.0)])
        advanced_page("L-system", [("lsystem_seed", "int", 0, -2147483648, 2147483647), ("lsystem_iterations", "int", 4, 1, 8), ("lsystem_angle", "float", 25.0, -180.0, 180.0), ("lsystem_length", "float", 0.18, 0.001, 1.0), ("lsystem_reduction", "float", 0.7, 0.1, 0.99)])
        advanced_page("Cracks", [("crack_seed", "int", 0, -2147483648, 2147483647), ("crack_count", "int", 12, 1, 512), ("crack_steps", "int", 80, 1, 2000), ("crack_step_length", "float", 0.02, 0.001, 0.2), ("crack_thickness", "float", 0.01, 0.001, 0.2)])
        advanced_page("Penrose", [("penrose_seed", "int", 0, -2147483648, 2147483647), ("penrose_scale", "float", 8.0, 0.1, 64.0), ("penrose_line_width", "float", 0.18, 0.01, 1.0), ("penrose_rotation", "float", 0.0, -6.28, 6.28)])
        advanced_page("Truchet", [("truchet_seed", "int", 0, -2147483648, 2147483647), ("truchet_scale", "float", 8.0, 0.1, 64.0), ("truchet_line_width", "float", 0.18, 0.01, 1.0)])
        advanced_page("Superformula", [("superformula_m", "float", 5.0, 0.1, 32.0), ("superformula_n1", "float", 0.3, 0.01, 8.0), ("superformula_n2", "float", 1.0, 0.01, 8.0), ("superformula_n3", "float", 1.0, 0.01, 8.0), ("superformula_scale", "float", 0.35, 0.01, 1.0), ("superformula_edge_softness", "float", 0.05, 0.001, 1.0)])
        advanced_page("Gaussian peaks", [("gaussian_seed", "int", 0, -2147483648, 2147483647), ("gaussian_count", "int", 8, 1, 128), ("gaussian_width", "float", 0.12, 0.01, 1.0), ("gaussian_height", "float", 1.0, 0.01, 4.0), ("gaussian_crater", "check", False, 0, 1)])
        advanced_page("Julia", [("julia_center_real", "float", 0.0, -2.0, 2.0), ("julia_center_imaginary", "float", 0.0, -2.0, 2.0), ("julia_constant_real", "float", -0.7, -2.0, 2.0), ("julia_constant_imaginary", "float", 0.27015, -2.0, 2.0), ("julia_zoom", "float", 1.0, 0.1, 1000.0), ("julia_iterations", "int", 100, 1, 2000), ("julia_contrast", "float", 1.0, 0.1, 10.0), ("julia_invert", "check", False, 0, 1)])
        advanced_page("Moiré", [("moire_frequency_a", "float", 8.0, 0.1, 64.0), ("moire_frequency_b", "float", 8.5, 0.1, 64.0), ("moire_angle_a", "float", 0.0, -6.28, 6.28), ("moire_angle_b", "float", 0.35, -6.28, 6.28), ("moire_phase_a", "float", 0.0, -6.28, 6.28), ("moire_phase_b", "float", 0.0, -6.28, 6.28), ("moire_radial", "check", False, 0, 1)])
        advanced_page("Gabor", [("gabor_seed", "int", 0, -2147483648, 2147483647), ("gabor_frequency", "float", 12.0, 0.1, 128.0), ("gabor_orientation", "float", 0.0, -6.28, 6.28), ("gabor_sigma", "float", 0.08, 0.001, 1.0), ("gabor_components", "int", 4, 1, 64)])

        self.procedural_stack.addWidget(noise_page)
        self.procedural_stack.addWidget(wave_page)
        self.procedural_stack.addWidget(mandelbrot_page)
        self.procedural_stack.addWidget(voronoi_page)
        self.procedural_stack.addWidget(ridged_page)
        self.procedural_stack.addWidget(warped_page)
        self.procedural_stack.addWidget(sdf_page)
        for page in advanced_pages:
            self.procedural_stack.addWidget(page)
        qfractal_page = QWidget()
        qfractal_layout = QVBoxLayout(qfractal_page)
        self.qfractal_load_button = QPushButton("Load QFractalNow Config…")
        self.qfractal_status = QLabel("No QFractalNow config loaded")
        self.qfractal_status.setWordWrap(True)
        self.qfractal_load_button.clicked.connect(self._choose_qfractal_config)
        qfractal_layout.addWidget(self.qfractal_load_button)
        qfractal_layout.addWidget(self.qfractal_status)
        self.procedural_stack.addWidget(qfractal_page)
        for control in controls.values():
            if hasattr(control, "valueChanged"):
                control.valueChanged.connect(self._procedural_changed)
            elif hasattr(control, "currentTextChanged"):
                control.currentTextChanged.connect(self._procedural_changed)
            else:
                control.toggled.connect(self._procedural_changed)
        return controls

    def _build_composition_controls(self) -> dict[str, object]:
        controls: dict[str, object] = {}
        box = QWidget()
        form = QFormLayout(box)
        controls["box"] = box
        controls["enabled"] = QCheckBox("Enable secondary field")
        secondary_sources = ["Fractal noise", "Wave interference", "Mandelbrot", "Voronoi", "Ridged noise", "Warped noise", "SDF shapes", "Chladni", "Spectral", "Reaction-diffusion", "Phyllotaxis", "Cellular automata", "Flow field", "Erosion", "L-system", "Cracks", "Penrose", "Truchet", "Superformula", "Gaussian peaks", "Julia", "Moiré", "Gabor", "Imported heightmap", "Primary source"]
        controls["source"] = QComboBox(); controls["source"].addItems(secondary_sources)
        controls["seed"] = QSpinBox(); controls["seed"].setRange(-2147483648, 2147483647); controls["seed"].setValue(17)
        controls["frequency"] = QDoubleSpinBox(); controls["frequency"].setRange(0.1, 64.0); controls["frequency"].setValue(4.0); controls["frequency"].setSingleStep(0.1)
        controls["octaves"] = QSpinBox(); controls["octaves"].setRange(1, 12); controls["octaves"].setValue(4)
        controls["persistence"] = QDoubleSpinBox(); controls["persistence"].setRange(0.0, 1.0); controls["persistence"].setValue(0.5); controls["persistence"].setSingleStep(0.05)
        controls["operation"] = QComboBox(); controls["operation"].addItems(["Blend", "Add", "Subtract", "Multiply", "Minimum", "Maximum"])
        controls["amount"] = QDoubleSpinBox(); controls["amount"].setRange(0.0, 1.0); controls["amount"].setValue(0.5); controls["amount"].setSingleStep(0.05)
        controls["secondary_gamma"] = QDoubleSpinBox(); controls["secondary_gamma"].setRange(0.1, 5.0); controls["secondary_gamma"].setValue(1.0); controls["secondary_gamma"].setSingleStep(0.05)
        controls["secondary_contrast"] = QDoubleSpinBox(); controls["secondary_contrast"].setRange(0.0, 4.0); controls["secondary_contrast"].setValue(1.0); controls["secondary_contrast"].setSingleStep(0.05)
        controls["secondary_blur"] = QDoubleSpinBox(); controls["secondary_blur"].setRange(0.0, 20.0); controls["secondary_blur"].setSingleStep(0.1)
        controls["secondary_invert"] = QCheckBox("Invert secondary")
        controls["mask_enabled"] = QCheckBox("Use radial mask")
        controls["mask_radius"] = QDoubleSpinBox(); controls["mask_radius"].setRange(0.01, 1.5); controls["mask_radius"].setValue(0.7); controls["mask_radius"].setSingleStep(0.05)
        controls["mask_feather"] = QDoubleSpinBox(); controls["mask_feather"].setRange(0.0, 1.0); controls["mask_feather"].setValue(0.1); controls["mask_feather"].setSingleStep(0.05)
        controls["mask_invert"] = QCheckBox("Invert mask")
        controls["import_secondary"] = QPushButton("Import Secondary Heightmap…")
        controls["import_mask"] = QPushButton("Import Mask…")
        controls["copy_primary"] = QPushButton("Copy Primary Source")
        controls["wave_mode"] = QComboBox(); controls["wave_mode"].addItems(["Planar", "Radial"])
        controls["wave_frequency_x"] = QDoubleSpinBox(); controls["wave_frequency_x"].setRange(0.1, 64.0); controls["wave_frequency_x"].setValue(4.0)
        controls["wave_frequency_y"] = QDoubleSpinBox(); controls["wave_frequency_y"].setRange(0.1, 64.0); controls["wave_frequency_y"].setValue(4.0)
        controls["wave_amplitude_x"] = QDoubleSpinBox(); controls["wave_amplitude_x"].setRange(-1.0, 1.0); controls["wave_amplitude_x"].setValue(1.0); controls["wave_amplitude_x"].setSingleStep(0.05)
        controls["wave_amplitude_y"] = QDoubleSpinBox(); controls["wave_amplitude_y"].setRange(-1.0, 1.0); controls["wave_amplitude_y"].setValue(1.0); controls["wave_amplitude_y"].setSingleStep(0.05)
        controls["wave_output_amplitude"] = QDoubleSpinBox(); controls["wave_output_amplitude"].setRange(0.0, 1.0); controls["wave_output_amplitude"].setValue(1.0); controls["wave_output_amplitude"].setSingleStep(0.05)
        controls["mandelbrot_center_real"] = QDoubleSpinBox(); controls["mandelbrot_center_real"].setRange(-2.0, 2.0); controls["mandelbrot_center_real"].setValue(-0.5); controls["mandelbrot_center_real"].setSingleStep(0.05)
        controls["mandelbrot_center_imaginary"] = QDoubleSpinBox(); controls["mandelbrot_center_imaginary"].setRange(-2.0, 2.0); controls["mandelbrot_center_imaginary"].setValue(0.0); controls["mandelbrot_center_imaginary"].setSingleStep(0.05)
        controls["mandelbrot_zoom"] = QDoubleSpinBox(); controls["mandelbrot_zoom"].setRange(0.1, 1000.0); controls["mandelbrot_zoom"].setValue(1.0); controls["mandelbrot_zoom"].setSingleStep(0.1)
        controls["mandelbrot_iterations"] = QSpinBox(); controls["mandelbrot_iterations"].setRange(1, 2000); controls["mandelbrot_iterations"].setValue(100)
        controls["mandelbrot_contrast"] = QDoubleSpinBox(); controls["mandelbrot_contrast"].setRange(0.1, 10.0); controls["mandelbrot_contrast"].setValue(1.0); controls["mandelbrot_contrast"].setSingleStep(0.1)
        controls["mandelbrot_invert"] = QCheckBox("Invert escape field")
        fractal_page = QWidget(); fractal_form = QFormLayout(fractal_page)
        for label, name in (("Seed", "seed"), ("Base frequency", "frequency"), ("Octaves", "octaves"), ("Persistence", "persistence")):
            fractal_form.addRow(label, controls[name])
        wave_page = QWidget(); wave_form = QFormLayout(wave_page)
        for label, name in (("Mode", "wave_mode"), ("Frequency X", "wave_frequency_x"), ("Frequency Y", "wave_frequency_y"), ("Amplitude X", "wave_amplitude_x"), ("Amplitude Y", "wave_amplitude_y"), ("Output amplitude", "wave_output_amplitude")):
            wave_form.addRow(label, controls[name])
        mandelbrot_page = QWidget(); mandelbrot_form = QFormLayout(mandelbrot_page)
        for label, name in (("Center real", "mandelbrot_center_real"), ("Center imaginary", "mandelbrot_center_imaginary"), ("Zoom", "mandelbrot_zoom"), ("Iterations", "mandelbrot_iterations"), ("Contrast", "mandelbrot_contrast")):
            mandelbrot_form.addRow(label, controls[name])
        mandelbrot_form.addRow(controls["mandelbrot_invert"])
        fallback_pages = [QLabel(f"{source} uses its generator defaults in composition.") for source in secondary_sources[3:-2]]
        imported_page = QLabel("Imported heightmap uses its source pixels directly.")
        primary_page = QLabel("Uses the current primary source.")
        controls["secondary_stack"] = QStackedWidget()
        for page in (fractal_page, wave_page, mandelbrot_page, *fallback_pages, imported_page, primary_page):
            controls["secondary_stack"].addWidget(page)
        for label, name in (("Secondary source", "source"),):
            form.addRow(label, controls[name])
        form.addRow("Source parameters", controls["secondary_stack"])
        for label, name in (("Secondary gamma", "secondary_gamma"), ("Secondary contrast", "secondary_contrast"), ("Secondary blur", "secondary_blur"), ("Operation", "operation"), ("Amount", "amount"), ("Mask radius", "mask_radius"), ("Mask feather", "mask_feather")):
            form.addRow(label, controls[name])
        form.insertRow(0, controls["enabled"])
        form.addRow(controls["copy_primary"])
        form.addRow(controls["mask_enabled"])
        form.addRow(controls["mask_invert"])
        form.addRow(controls["secondary_invert"])
        form.addRow(controls["import_secondary"])
        form.addRow(controls["import_mask"])
        controls["import_secondary"].clicked.connect(self._choose_secondary_field)
        controls["import_mask"].clicked.connect(self._choose_mask_field)
        controls["copy_primary"].clicked.connect(self._copy_primary_to_secondary)
        controls["source"].currentTextChanged.connect(self._secondary_source_changed)
        for control in controls.values():
            if control is box or control is controls["source"] or control is controls["secondary_stack"] or isinstance(control, QPushButton):
                continue
            if hasattr(control, "valueChanged"):
                control.valueChanged.connect(self._composition_changed)
            elif hasattr(control, "currentTextChanged"):
                control.currentTextChanged.connect(self._composition_changed)
            else:
                control.toggled.connect(self._composition_changed)
        return controls

    def _secondary_source_changed(self, source: str) -> None:
        index = self.composition_controls["source"].findText(source)
        index = max(0, index)
        self.composition_controls["secondary_stack"].setCurrentIndex(index)
        self._composition_changed()

    def _copy_primary_to_secondary(self) -> None:
        if not self.is_procedural and self.state.source_image is None:
            return
        self.state.secondary_source_descriptor = dict(self.state.source_descriptor)
        self.state.secondary_field = None
        self.state.secondary_field_name = None
        self.state.secondary_original_bytes = None
        self.composition_controls["source"].setCurrentText("Primary source")
        self.composition_controls["enabled"].setChecked(True)
        self.parameters_changed.emit()
        self.procedural_source_changed.emit()

    def _choose_secondary_field(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Secondary Heightmap", "", "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)")
        if path:
            self._start_external_import(path, "secondary")

    def _choose_mask_field(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Mask", "", "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)")
        if path:
            self._start_external_import(path, "mask")

    def _start_external_import(self, path: str, kind: str) -> None:
        if self._external_import_worker is not None:
            return
        self.external_status.setText(f"Importing {Path(path).name}…")
        self._external_import_generation += 1
        generation = self._external_import_generation
        worker = FunctionWorker(_load_external_field, path)
        self._external_import_worker = worker
        worker.signals.finished.connect(lambda result, selected=kind, token=generation: self._external_import_finished(token, selected, result))
        worker.signals.failed.connect(lambda message, token=generation: self._external_import_failed(token, message))
        self.thread_pool.start(worker)

    def _external_import_finished(self, generation: int, kind: str, result) -> None:
        if generation != self._external_import_generation:
            return
        self._external_import_worker = None
        field, name, content_hash, original = result
        field = np.array(field, dtype=np.float32, copy=True)
        field.setflags(write=False)
        descriptor = SourceDescriptor("heightmap", parameters={"filename": name}, algorithm="imported_heightmap", algorithm_version="1", content_hash=content_hash)
        if kind == "secondary":
            self.state.secondary_field = field
            self.state.secondary_field_name = name
            self.state.secondary_original_bytes = original
            self.state.secondary_source_descriptor = descriptor.to_dict()
            self.composition_controls["source"].setCurrentText("Imported heightmap")
            self.composition_controls["enabled"].setChecked(True)
        else:
            self.state.mask_field = field
            self.state.mask_field_name = name
            self.state.mask_original_bytes = original
            self.state.mask_source_descriptor = descriptor.to_dict()
            self.composition_controls["mask_enabled"].setChecked(True)
        self._restore_composition_controls()
        self.external_status.setText(f"Imported {name}")
        self._update_provenance()
        self.parameters_changed.emit()
        self._update_composition_state()
        if kind == "mask":
            self.state.mask_source_descriptor = descriptor.to_dict()
        self.procedural_source_changed.emit()

    def _external_import_failed(self, generation: int, message: str) -> None:
        if generation != self._external_import_generation:
            return
        self._external_import_worker = None
        self.external_status.setText(f"Import failed: {message}")

    def _secondary_descriptor(self) -> SourceDescriptor:
        c = self.composition_controls
        mode = c["source"].currentText().lower()
        if mode == "primary source" and self.state.source_descriptor:
            return SourceDescriptor.from_dict(self.state.source_descriptor)
        if mode == "imported heightmap" and self.state.secondary_source_descriptor is not None:
            return SourceDescriptor.from_dict(self.state.secondary_source_descriptor)
        if mode == "fractal noise":
            parameters = NoiseParameters(seed=c["seed"].value(), base_frequency=c["frequency"].value(), octaves=c["octaves"].value(), persistence=c["persistence"].value(), lacunarity=2.0, amplitude=1.0, normalization="auto", tileable=False)
            return SourceDescriptor("fractal_noise", parameters=parameters.__dict__.copy(), algorithm="value_fbm", algorithm_version="1", seed=parameters.seed)
        if mode == "wave interference":
            parameters = WaveParameters(mode=c["wave_mode"].currentText().lower(), frequency_x=c["wave_frequency_x"].value(), frequency_y=c["wave_frequency_y"].value(), amplitude_x=c["wave_amplitude_x"].value(), amplitude_y=c["wave_amplitude_y"].value(), output_amplitude=c["wave_output_amplitude"].value())
            return SourceDescriptor("wave_interference", parameters=parameters.__dict__.copy(), algorithm="wave_interference", algorithm_version="1")
        if mode == "mandelbrot":
            parameters = MandelbrotParameters(center_real=c["mandelbrot_center_real"].value(), center_imaginary=c["mandelbrot_center_imaginary"].value(), zoom=c["mandelbrot_zoom"].value(), iterations=c["mandelbrot_iterations"].value(), contrast=c["mandelbrot_contrast"].value(), invert=c["mandelbrot_invert"].isChecked())
            return SourceDescriptor("mandelbrot", parameters=parameters.__dict__.copy(), algorithm="smooth_escape_time", algorithm_version="1")
        pattern_defaults = {
            "voronoi": ("voronoi", {"seed": c["seed"].value(), "cell_density": c["frequency"].value(), "jitter": 1.0, "mode": "boundary", "edge_width": .15, "normalization": "auto"}, "voronoi"),
            "ridged noise": ("ridged_noise", {"seed": c["seed"].value(), "base_frequency": c["frequency"].value(), "octaves": c["octaves"].value(), "persistence": c["persistence"].value(), "lacunarity": 2.0, "sharpness": 2.0}, "ridged_fbm"),
            "warped noise": ("warped_noise", {"seed": c["seed"].value(), "base_frequency": c["frequency"].value(), "warp_frequency": c["frequency"].value(), "warp_strength": .25, "octaves": c["octaves"].value(), "persistence": c["persistence"].value(), "lacunarity": 2.0}, "domain_warped_fbm"),
            "sdf shapes": ("sdf", {"shape": "circle", "radius": .35, "width": .6, "height": .6, "repeats_x": 1, "repeats_y": 1, "edge_softness": .05, "invert": False}, "sdf_circle"),
            "chladni": ("chladni", {"mode_x": 3, "mode_y": 5, "phase": 0.0, "threshold": 0.0, "line_width": .2}, "chladni_modes"),
            "spectral": ("spectral", {"seed": c["seed"].value(), "components": 12, "minimum_frequency": 1.0, "maximum_frequency": 12.0, "anisotropy": 1.0, "amplitude_falloff": 1.0}, "random_fourier"),
            "reaction-diffusion": ("reaction_diffusion", {"seed": c["seed"].value(), "iterations": 300, "feed": .055, "kill": .062, "diffusion_a": 1.0, "diffusion_b": .5}, "gray_scott"),
            "phyllotaxis": ("phyllotaxis", {"count": 500, "divergence_degrees": 137.5, "growth": .018, "point_radius": .025, "invert": False}, "golden_angle"),
            "cellular automata": ("cellular_automata", {"seed": c["seed"].value(), "iterations": 10, "initial_density": .45, "birth_limit": 4, "survival_limit": 4}, "life_neighbors"),
            "flow field": ("flow_field", {"frequency": c["frequency"].value(), "swirl": 1.0, "radial": False, "bands": 8}, "flow_bands"),
            "erosion": ("erosion", {"seed": c["seed"].value(), "iterations": 50, "strength": .25, "evaporation": .1}, "bounded_erosion"),
            "l-system": ("lsystem", {"seed": c["seed"].value(), "iterations": 4, "branch_angle_degrees": 25.0, "length": .18, "length_reduction": .7, "thickness": .025, "branch_probability": .85}, "branching_growth"),
            "cracks": ("cracks", {"seed": c["seed"].value(), "cracks": 12, "steps": 80, "step_length": .02, "branch_probability": .08, "thickness": .01}, "random_walk_cracks"),
            "penrose": ("penrose", {"seed": c["seed"].value(), "scale": 8.0, "line_width": .18, "rotation": 0.0}, "golden_interference"),
            "truchet": ("truchet", {"seed": c["seed"].value(), "scale": 8.0, "line_width": .18, "rotation": 0.0}, "diagonal_tiles"),
        }
        if mode in pattern_defaults:
            source_type, parameters, algorithm = pattern_defaults[mode]
            return SourceDescriptor(source_type, parameters=parameters, algorithm=algorithm, algorithm_version="1", seed=parameters.get("seed"))
        parameters = MandelbrotParameters(zoom=max(0.1, c["frequency"].value()), iterations=100, contrast=1.0, invert=False)
        return SourceDescriptor("mandelbrot", parameters=parameters.__dict__.copy(), algorithm="smooth_escape_time", algorithm_version="1")

    def _update_composition_state(self) -> None:
        c = self.composition_controls
        enabled = c["enabled"].isChecked()
        if enabled and not self.compose_toggle.isChecked():
            self.compose_toggle.setChecked(True)
        self.state.composition_settings = {
            "enabled": enabled,
            "operation": c["operation"].currentText().lower(),
            "amount": c["amount"].value(),
            "range_policy": "clip",
        }
        self.state.secondary_processing_settings = {
            "input_gamma": c["secondary_gamma"].value(),
            "contrast": c["secondary_contrast"].value(),
            "blur_radius": c["secondary_blur"].value(),
            "inverted": c["secondary_invert"].isChecked(),
        }
        self.state.secondary_source_descriptor = self._secondary_descriptor().to_dict() if enabled else None
        self.state.mask_source_descriptor = SourceDescriptor(
            "radial_mask",
            parameters={"inner_radius": max(0.0, c["mask_radius"].value() - c["mask_feather"].value()), "outer_radius": c["mask_radius"].value(), "invert": c["mask_invert"].isChecked()},
        ).to_dict() if enabled and c["mask_enabled"].isChecked() else None

    def _composition_changed(self, *args) -> None:
        if not self.is_procedural and self.state.source_image is None:
            return
        self._update_composition_state()
        self.procedural_source_changed.emit()
        self.parameters_changed.emit()

    @property
    def is_procedural(self) -> bool:
        return self.source_mode.currentIndex() != 0

    def procedural_descriptor(self) -> SourceDescriptor:
        """Return the current procedural controls as a validated descriptor."""
        c = self.procedural_controls
        if self.source_mode.currentIndex() == 1:
            parameters = NoiseParameters(
                seed=c["noise_seed"].value(), base_frequency=c["noise_frequency"].value(), octaves=c["noise_octaves"].value(),
                persistence=c["noise_persistence"].value(), lacunarity=c["noise_lacunarity"].value(), amplitude=c["noise_amplitude"].value(),
                normalization=c["noise_normalization"].currentText().lower(), tileable=c["noise_tileable"].isChecked(),
            )
            return SourceDescriptor("fractal_noise", parameters=parameters.__dict__.copy(), algorithm="value_fbm", algorithm_version="1", seed=parameters.seed)
        if self.source_mode.currentIndex() == 2:
            parameters = WaveParameters(
                mode=c["wave_mode"].currentText().lower(), frequency_x=c["wave_frequency_x"].value(), frequency_y=c["wave_frequency_y"].value(),
                amplitude_x=c["wave_amplitude_x"].value(), amplitude_y=c["wave_amplitude_y"].value(), output_amplitude=c["wave_output_amplitude"].value(),
            )
            return SourceDescriptor("wave_interference", parameters=parameters.__dict__.copy(), algorithm="wave_interference", algorithm_version="1")
        if self.source_mode.currentIndex() == 3:
            parameters = MandelbrotParameters(
            center_real=c["mandelbrot_center_real"].value(), center_imaginary=c["mandelbrot_center_imaginary"].value(),
            zoom=c["mandelbrot_zoom"].value(), iterations=c["mandelbrot_iterations"].value(), contrast=c["mandelbrot_contrast"].value(), invert=c["mandelbrot_invert"].isChecked(),
            )
            return SourceDescriptor("mandelbrot", parameters=parameters.__dict__.copy(), algorithm="smooth_escape_time", algorithm_version="1")
        if self.source_mode.currentIndex() == 4:
            return SourceDescriptor("voronoi", parameters={"seed": c["voronoi_seed"].value(), "cell_density": c["voronoi_density"].value(), "jitter": c["voronoi_jitter"].value(), "mode": c["voronoi_mode"].currentText().lower(), "edge_width": 0.15, "normalization": "auto"}, algorithm="voronoi", algorithm_version="1", seed=c["voronoi_seed"].value())
        if self.source_mode.currentIndex() == 5:
            return SourceDescriptor("ridged_noise", parameters={"seed": c["ridged_seed"].value(), "base_frequency": c["ridged_frequency"].value(), "octaves": c["ridged_octaves"].value(), "persistence": 0.5, "lacunarity": 2.0, "sharpness": c["ridged_sharpness"].value()}, algorithm="ridged_fbm", algorithm_version="1", seed=c["ridged_seed"].value())
        if self.source_mode.currentIndex() == 6:
            return SourceDescriptor("warped_noise", parameters={"seed": c["warped_seed"].value(), "base_frequency": c["warped_frequency"].value(), "warp_frequency": c["warped_warp_frequency"].value(), "warp_strength": c["warped_strength"].value(), "octaves": c["warped_octaves"].value(), "persistence": 0.5, "lacunarity": 2.0}, algorithm="domain_warped_fbm", algorithm_version="1", seed=c["warped_seed"].value())
        if self.source_mode.currentIndex() == 7:
            return SourceDescriptor("sdf", parameters={"shape": c["sdf_shape"].currentText().lower(), "radius": c["sdf_radius"].value(), "width": c["sdf_width"].value(), "height": c["sdf_height"].value(), "repeats_x": c["sdf_repeats_x"].value(), "repeats_y": c["sdf_repeats_y"].value(), "edge_softness": c["sdf_softness"].value(), "invert": c["sdf_invert"].isChecked(), "boolean_shape": c["sdf_boolean_shape"].currentText().lower(), "boolean_operation": c["sdf_boolean_operation"].currentText().lower(), "boolean_offset_x": c["sdf_boolean_offset_x"].value(), "boolean_offset_y": c["sdf_boolean_offset_y"].value()}, algorithm=f"sdf_{c['sdf_shape'].currentText().lower()}", algorithm_version="1")
        if self.source_mode.currentIndex() == 24:
            parameters = self.state.source_descriptor.get("parameters", {}) if self.state.source_descriptor.get("type") == "qfractalnow_config" else {}
            return SourceDescriptor("qfractalnow_config", parameters={"filename": parameters.get("filename", ""), "config_text": parameters.get("config_text", "")}, algorithm="fractalnow", algorithm_version="1")
        if self.source_mode.currentIndex() == 19:
            parameters = {"m": c["superformula_m"].value(), "n1": c["superformula_n1"].value(), "n2": c["superformula_n2"].value(), "n3": c["superformula_n3"].value(), "scale": c["superformula_scale"].value(), "edge_softness": c["superformula_edge_softness"].value()}
            return SourceDescriptor("superformula", parameters=parameters, algorithm="superformula", algorithm_version="1")
        if self.source_mode.currentIndex() == 20:
            parameters = {"seed": c["gaussian_seed"].value(), "count": c["gaussian_count"].value(), "width": c["gaussian_width"].value(), "height": c["gaussian_height"].value(), "crater": c["gaussian_crater"].isChecked()}
            return SourceDescriptor("gaussian_peaks", parameters=parameters, algorithm="gaussian_clusters", algorithm_version="1", seed=parameters["seed"])
        if self.source_mode.currentIndex() == 21:
            parameters = {"center_real": c["julia_center_real"].value(), "center_imaginary": c["julia_center_imaginary"].value(), "constant_real": c["julia_constant_real"].value(), "constant_imaginary": c["julia_constant_imaginary"].value(), "zoom": c["julia_zoom"].value(), "iterations": c["julia_iterations"].value(), "contrast": c["julia_contrast"].value(), "invert": c["julia_invert"].isChecked()}
            return SourceDescriptor("julia", parameters=parameters, algorithm="julia_escape_time", algorithm_version="1")
        if self.source_mode.currentIndex() == 22:
            parameters = {"frequency_a": c["moire_frequency_a"].value(), "frequency_b": c["moire_frequency_b"].value(), "angle_a": c["moire_angle_a"].value(), "angle_b": c["moire_angle_b"].value(), "phase_a": c["moire_phase_a"].value(), "phase_b": c["moire_phase_b"].value(), "radial": c["moire_radial"].isChecked()}
            return SourceDescriptor("moire", parameters=parameters, algorithm="dual_interference", algorithm_version="1")
        if self.source_mode.currentIndex() == 23:
            parameters = {"seed": c["gabor_seed"].value(), "frequency": c["gabor_frequency"].value(), "orientation": c["gabor_orientation"].value(), "sigma": c["gabor_sigma"].value(), "components": c["gabor_components"].value()}
            return SourceDescriptor("gabor", parameters=parameters, algorithm="gabor_bank", algorithm_version="1", seed=parameters["seed"])
        defaults = {
            8: ("chladni", {"mode_x": c["chladni_mode_x"].value(), "mode_y": c["chladni_mode_y"].value(), "phase": c["chladni_phase"].value(), "threshold": 0.0, "line_width": c["chladni_line_width"].value()}, "chladni_modes"),
            9: ("spectral", {"seed": c["spectral_seed"].value(), "components": c["spectral_components"].value(), "minimum_frequency": c["spectral_min_frequency"].value(), "maximum_frequency": c["spectral_max_frequency"].value(), "anisotropy": 1.0, "amplitude_falloff": 1.0}, "random_fourier"),
            10: ("reaction_diffusion", {"seed": c["reaction_seed"].value(), "iterations": c["reaction_iterations"].value(), "feed": c["reaction_feed"].value(), "kill": c["reaction_kill"].value(), "diffusion_a": 1.0, "diffusion_b": 0.5}, "gray_scott"),
            11: ("phyllotaxis", {"count": c["phyllotaxis_count"].value(), "divergence_degrees": c["phyllotaxis_divergence"].value(), "growth": c["phyllotaxis_growth"].value(), "point_radius": c["phyllotaxis_radius"].value(), "invert": False}, "golden_angle"),
            12: ("cellular_automata", {"seed": c["cellular_seed"].value(), "iterations": c["cellular_iterations"].value(), "initial_density": c["cellular_density"].value(), "birth_limit": c["cellular_birth"].value(), "survival_limit": c["cellular_survival"].value()}, "life_neighbors"),
            13: ("flow_field", {"frequency": c["flow_frequency"].value(), "swirl": c["flow_swirl"].value(), "radial": False, "bands": c["flow_bands"].value()}, "flow_bands"),
            14: ("erosion", {"seed": c["erosion_seed"].value(), "iterations": c["erosion_iterations"].value(), "strength": c["erosion_strength"].value(), "evaporation": c["erosion_evaporation"].value()}, "bounded_erosion"),
            15: ("lsystem", {"seed": c["lsystem_seed"].value(), "iterations": c["lsystem_iterations"].value(), "branch_angle_degrees": c["lsystem_angle"].value(), "length": c["lsystem_length"].value(), "length_reduction": c["lsystem_reduction"].value(), "thickness": 0.025, "branch_probability": 0.85}, "branching_growth"),
            16: ("cracks", {"seed": c["crack_seed"].value(), "cracks": c["crack_count"].value(), "steps": c["crack_steps"].value(), "step_length": c["crack_step_length"].value(), "branch_probability": 0.08, "thickness": c["crack_thickness"].value()}, "random_walk_cracks"),
            17: ("penrose", {"seed": c["penrose_seed"].value(), "scale": c["penrose_scale"].value(), "line_width": c["penrose_line_width"].value(), "rotation": c["penrose_rotation"].value()}, "golden_interference"),
            18: ("truchet", {"seed": c["truchet_seed"].value(), "scale": c["truchet_scale"].value(), "line_width": c["truchet_line_width"].value(), "rotation": 0.0}, "diagonal_tiles"),
            19: ("superformula", {"m": 5.0, "n1": .3, "n2": 1.0, "n3": 1.0, "scale": .35, "edge_softness": .05}, "superformula"),
            20: ("gaussian_peaks", {"seed": 0, "count": 8, "width": .12, "height": 1.0, "crater": False}, "gaussian_clusters"),
            21: ("julia", {"center_real": 0.0, "center_imaginary": 0.0, "constant_real": -.7, "constant_imaginary": .27015, "zoom": 1.0, "iterations": 100, "contrast": 1.0, "invert": False}, "julia_escape_time"),
            22: ("moire", {"frequency_a": 8.0, "frequency_b": 8.5, "angle_a": 0.0, "angle_b": .35, "phase_a": 0.0, "phase_b": 0.0, "radial": False}, "dual_interference"),
            23: ("gabor", {"seed": 0, "frequency": 12.0, "orientation": 0.0, "sigma": .08, "components": 4}, "gabor_bank"),
        }
        source_type, parameters, algorithm = defaults[self.source_mode.currentIndex()]
        return SourceDescriptor(source_type, parameters=parameters, algorithm=algorithm, algorithm_version="1", seed=parameters.get("seed"))

    def _randomize_source(self) -> None:
        if not self.is_procedural:
            return
        rng = np.random.default_rng()
        for name in ("noise_seed", "voronoi_seed", "ridged_seed", "warped_seed", "spectral_seed", "reaction_seed", "cellular_seed", "erosion_seed", "lsystem_seed", "crack_seed", "penrose_seed", "truchet_seed"):
            if name in self.procedural_controls:
                control = self.procedural_controls[name]
                control.setValue(int(rng.integers(-2_147_483_648, 2_147_483_647)))
        self._procedural_changed()

    def _reset_source(self) -> None:
        if not self.is_procedural:
            return
        defaults = {
            "noise_seed": 0, "noise_frequency": 2.0, "noise_octaves": 6, "noise_persistence": 0.5, "noise_lacunarity": 2.0, "noise_amplitude": 1.0,
            "voronoi_seed": 0, "voronoi_density": 8.0, "voronoi_jitter": 1.0,
            "ridged_seed": 0, "ridged_frequency": 2.0, "ridged_octaves": 6, "ridged_sharpness": 2.0,
            "warped_seed": 0, "warped_frequency": 2.0, "warped_warp_frequency": 2.0, "warped_strength": 0.25, "warped_octaves": 5,
            "spectral_seed": 0, "spectral_components": 12, "spectral_min_frequency": 1.0, "spectral_max_frequency": 12.0,
            "reaction_seed": 0, "reaction_iterations": 300, "reaction_feed": 0.055, "reaction_kill": 0.062,
            "phyllotaxis_count": 500, "phyllotaxis_divergence": 137.5, "phyllotaxis_growth": 0.018, "phyllotaxis_radius": 0.025,
            "cellular_seed": 0, "cellular_iterations": 10, "cellular_density": 0.45, "cellular_birth": 4, "cellular_survival": 4,
            "flow_frequency": 4.0, "flow_swirl": 1.0, "flow_bands": 8,
            "erosion_seed": 0, "erosion_iterations": 50, "erosion_strength": 0.25, "erosion_evaporation": 0.1,
            "lsystem_seed": 0, "lsystem_iterations": 4, "lsystem_angle": 25.0, "lsystem_length": 0.18, "lsystem_reduction": 0.7,
            "crack_seed": 0, "crack_count": 12, "crack_steps": 80, "crack_step_length": 0.02, "crack_thickness": 0.01,
            "penrose_seed": 0, "penrose_scale": 8.0, "penrose_line_width": 0.18, "penrose_rotation": 0.0,
            "truchet_seed": 0, "truchet_scale": 8.0, "truchet_line_width": 0.18,
        }
        for name, value in defaults.items():
            if name in self.procedural_controls:
                self.procedural_controls[name].setValue(value)
        self._procedural_changed()

    def _source_mode_changed(self, index: int, *, refresh: bool = True) -> None:
        self._cancel_external_import()
        self.procedural_stack.setCurrentIndex(max(0, index - 1))
        procedural = index != 0
        self.procedural_stack.setEnabled(procedural)
        self.procedural_stack.setVisible(procedural)
        self.source_randomize.setVisible(procedural)
        self.source_reset.setVisible(procedural)
        self.load_button.setVisible(not procedural)
        QTimer.singleShot(0, self._fit_source_section)
        self.composition_controls["box"].setEnabled(procedural or self.state.source_image is not None)
        for widget in (self.grayscale_button, self.invert_button, self.threshold_enabled, self.linear_light, self.curve_interpolation, self.reset_button, *self.crop_controls, self.resize_enabled, self.resize_width, self.resize_height, *self.controls.values()):
            widget.setEnabled(not procedural)
        if procedural:
            if index == 24 and self.state.source_descriptor.get("type") != "qfractalnow_config":
                self.info.setText("Load a QFractalNow .config file")
                return
            self.state.source_type = self.procedural_descriptor().source_type
            self.state.source_descriptor = self.procedural_descriptor().to_dict()
            self.state.pipeline_snapshot = None
            self.info.setText("Procedural source")
            self._update_provenance()
            self._refresh_preview()
            self.procedural_source_changed.emit()
            self.parameters_changed.emit()
        elif self.state.source_image is not None:
            self.state.source_type = "image"
            self.state.source_descriptor = {"type": "image", "schema_version": 1, "parameters": {}}
            if refresh:
                self._refresh_adjustments()
            self._update_provenance()

    def _fit_source_section(self) -> None:
        """Keep source metadata directly below the active generator controls."""
        if self.procedural_stack.isVisible() and self.procedural_stack.currentWidget() is not None:
            page = self.procedural_stack.currentWidget()
            page.adjustSize()
            self.procedural_stack.setFixedHeight(page.sizeHint().height())
        else:
            self.procedural_stack.setFixedHeight(0)
        self.source_content.setMaximumHeight(16_777_215)
        self.source_content.adjustSize()
        self.source_content.setFixedHeight(self.source_content.sizeHint().height())

    def _procedural_changed(self, *args) -> None:
        if not self.is_procedural:
            return
        descriptor = self.procedural_descriptor()
        self.state.source_type = descriptor.source_type
        self.state.source_descriptor = descriptor.to_dict()
        self.state.pipeline_snapshot = None
        self.info.setText(f"Procedural source: {descriptor.source_type}")
        self._update_provenance()
        self.procedural_source_changed.emit()
        self.parameters_changed.emit()

    def _restore_procedural_controls(self, descriptor: dict) -> None:
        """Reflect a loaded procedural descriptor without emitting edits."""
        parameters = descriptor.get("parameters", {})
        controls = self.procedural_controls
        for control in controls.values():
            control.blockSignals(True)
        try:
            for name, value in parameters.items():
                if name == "seed" and "noise_seed" in controls:
                    controls["noise_seed"].setValue(int(value))
                elif name == "base_frequency" and "noise_frequency" in controls:
                    controls["noise_frequency"].setValue(float(value))
                elif name in {"octaves", "iterations"}:
                    key = "noise_octaves" if name == "octaves" else "mandelbrot_iterations"
                    controls[key].setValue(int(value))
                elif name in {"persistence", "lacunarity", "amplitude"} and f"noise_{name}" in controls:
                    controls[f"noise_{name}"].setValue(float(value))
                elif name == "normalization" and "noise_normalization" in controls:
                    controls["noise_normalization"].setCurrentText(str(value).title())
                elif name == "tileable" and "noise_tileable" in controls:
                    controls["noise_tileable"].setChecked(bool(value))
                elif name in {"mode"} and "wave_mode" in controls:
                    controls["wave_mode"].setCurrentText(str(value).title())
                elif name in {"frequency_x", "frequency_y", "amplitude_x", "amplitude_y", "output_amplitude"}:
                    controls[f"wave_{name}"].setValue(float(value))
                elif name in {"center_real", "center_imaginary", "zoom", "contrast"}:
                    controls[f"mandelbrot_{name}"].setValue(float(value))
                elif name == "invert" and "mandelbrot_invert" in controls:
                    controls["mandelbrot_invert"].setChecked(bool(value))
                elif name in {"seed", "cell_density", "jitter", "edge_width"} and f"voronoi_{name if name != 'cell_density' else 'density'}" in controls:
                    controls[f"voronoi_{name if name != 'cell_density' else 'density'}"].setValue(float(value))
                elif name == "mode" and "voronoi_mode" in controls:
                    controls["voronoi_mode"].setCurrentText(str(value).title())
                elif name in {"base_frequency", "octaves", "sharpness"} and f"ridged_{name if name != 'base_frequency' else 'frequency'}" in controls:
                    controls[f"ridged_{name if name != 'base_frequency' else 'frequency'}"].setValue(float(value))
                elif name in {"warp_frequency", "warp_strength"} and f"warped_{name}" in controls:
                    controls[f"warped_{name}"].setValue(float(value))
                elif name == "seed" and "ridged_seed" in controls:
                    controls["ridged_seed"].setValue(int(value))
                elif name == "seed" and "warped_seed" in controls:
                    controls["warped_seed"].setValue(int(value))
                elif name in {"shape"} and "sdf_shape" in controls:
                    controls["sdf_shape"].setCurrentText(str(value).title())
                elif name in {"radius", "width", "height", "edge_softness"} and f"sdf_{name if name != 'edge_softness' else 'softness'}" in controls:
                    controls[f"sdf_{name if name != 'edge_softness' else 'softness'}"].setValue(float(value))
                elif name in {"repeats_x", "repeats_y"} and f"sdf_{name}" in controls:
                    controls[f"sdf_{name}"].setValue(int(value))
                elif name == "invert" and "sdf_invert" in controls:
                    controls["sdf_invert"].setChecked(bool(value))
            if descriptor.get("type") == "voronoi":
                controls["voronoi_seed"].setValue(int(parameters.get("seed", 0)))
                controls["voronoi_density"].setValue(float(parameters.get("cell_density", 8.0)))
                controls["voronoi_jitter"].setValue(float(parameters.get("jitter", 1.0)))
                controls["voronoi_mode"].setCurrentText(str(parameters.get("mode", "boundary")).title())
            elif descriptor.get("type") == "ridged_noise":
                controls["ridged_seed"].setValue(int(parameters.get("seed", 0)))
                controls["ridged_frequency"].setValue(float(parameters.get("base_frequency", 2.0)))
                controls["ridged_octaves"].setValue(int(parameters.get("octaves", 6)))
                controls["ridged_sharpness"].setValue(float(parameters.get("sharpness", 2.0)))
            elif descriptor.get("type") == "warped_noise":
                controls["warped_seed"].setValue(int(parameters.get("seed", 0)))
                controls["warped_frequency"].setValue(float(parameters.get("base_frequency", 2.0)))
                controls["warped_warp_frequency"].setValue(float(parameters.get("warp_frequency", 2.0)))
                controls["warped_strength"].setValue(float(parameters.get("warp_strength", 0.25)))
                controls["warped_octaves"].setValue(int(parameters.get("octaves", 5)))
            elif descriptor.get("type") == "sdf":
                controls["sdf_shape"].setCurrentText(str(parameters.get("shape", "circle")).title())
                controls["sdf_radius"].setValue(float(parameters.get("radius", 0.35)))
                controls["sdf_width"].setValue(float(parameters.get("width", 0.6)))
                controls["sdf_height"].setValue(float(parameters.get("height", 0.6)))
                controls["sdf_repeats_x"].setValue(int(parameters.get("repeats_x", 1)))
                controls["sdf_repeats_y"].setValue(int(parameters.get("repeats_y", 1)))
                controls["sdf_softness"].setValue(float(parameters.get("edge_softness", 0.05)))
                controls["sdf_invert"].setChecked(bool(parameters.get("invert", False)))
                controls["sdf_boolean_shape"].setCurrentText(str(parameters.get("boolean_shape", "none")).title())
                controls["sdf_boolean_operation"].setCurrentText(str(parameters.get("boolean_operation", "union")).title())
                controls["sdf_boolean_offset_x"].setValue(float(parameters.get("boolean_offset_x", 0.0)))
                controls["sdf_boolean_offset_y"].setValue(float(parameters.get("boolean_offset_y", 0.0)))
        finally:
            for control in controls.values():
                control.blockSignals(False)

    def _restore_composition_controls(self) -> None:
        controls = self.composition_controls
        settings = self.state.composition_settings or {}
        descriptor = self.state.secondary_source_descriptor or {}
        parameters = descriptor.get("parameters", {})
        for control in controls.values():
            if control is controls["box"]:
                continue
            control.blockSignals(True)
        try:
            controls["enabled"].setChecked(bool(settings.get("enabled", False)))
            self.compose_toggle.setChecked(bool(settings.get("enabled", False)))
            controls["operation"].setCurrentText(str(settings.get("operation", "blend")).title())
            controls["amount"].setValue(float(settings.get("amount", 0.5)))
            source_type = descriptor.get("type")
            source_label = "Primary source" if descriptor == self.state.source_descriptor else {"fractal_noise": "Fractal noise", "wave_interference": "Wave interference", "mandelbrot": "Mandelbrot", "heightmap": "Imported heightmap"}.get(source_type, "Fractal noise")
            controls["source"].setCurrentText(source_label)
            if "seed" in parameters:
                controls["seed"].setValue(int(parameters["seed"]))
            if "base_frequency" in parameters:
                controls["frequency"].setValue(float(parameters["base_frequency"]))
            elif "frequency_x" in parameters:
                controls["frequency"].setValue(float(parameters["frequency_x"]))
            elif "zoom" in parameters:
                controls["frequency"].setValue(float(parameters["zoom"]))
            if "octaves" in parameters:
                controls["octaves"].setValue(int(parameters["octaves"]))
            if "persistence" in parameters:
                controls["persistence"].setValue(float(parameters["persistence"]))
            mask = self.state.mask_source_descriptor
            mask_parameters = mask.get("parameters", {}) if mask else {}
            controls["mask_enabled"].setChecked(mask is not None)
            controls["mask_invert"].setChecked(bool(mask_parameters.get("invert", False)))
            controls["mask_radius"].setValue(float(mask_parameters.get("outer_radius", 0.7)))
            inner = float(mask_parameters.get("inner_radius", 0.0))
            controls["mask_feather"].setValue(max(0.0, controls["mask_radius"].value() - inner))
            secondary_processing = self.state.secondary_processing_settings or {}
            controls["secondary_gamma"].setValue(float(secondary_processing.get("input_gamma", 1.0)))
            controls["secondary_contrast"].setValue(float(secondary_processing.get("contrast", 1.0)))
            controls["secondary_blur"].setValue(float(secondary_processing.get("blur_radius", 0.0)))
            controls["secondary_invert"].setChecked(bool(secondary_processing.get("inverted", False)))
        finally:
            for control in controls.values():
                if control is not controls["box"]:
                    control.blockSignals(False)

    def dragEnterEvent(self, event) -> None:
        """Accept drops containing at least one supported image file."""
        if any(
            url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
            for url in event.mimeData().urls()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        """Load the first supported dropped image through the normal loader."""
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            candidate = Path(url.toLocalFile())
            if candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
                self.load_path(str(candidate))
                event.acceptProposedAction()
                return
        event.ignore()

    def _choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp)"
        )
        if path:
            self.load_path(path)

    def _choose_qfractal_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open QFractalNow Configuration", "", "QFractalNow config (*.config);;All files (*)")
        if not path:
            return
        try:
            config_text = Path(path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            self.error_occurred.emit(f"Could not read QFractalNow config: {error}")
            return
        descriptor = SourceDescriptor("qfractalnow_config", parameters={"filename": Path(path).name, "config_text": config_text}, algorithm="fractalnow", algorithm_version="1")
        self.state.source_type = descriptor.source_type
        self.state.source_descriptor = descriptor.to_dict()
        self.state.pipeline_snapshot = None
        self.qfractal_status.setText(f"Loaded {Path(path).name}; embedded in this project")
        self.info.setText(f"QFractalNow source: {Path(path).name}")
        self._update_provenance()
        self.procedural_source_changed.emit()
        self.parameters_changed.emit()

    def clear_preview(self) -> None:
        """Clear image controls and preview for a new project."""
        self._cancel_external_import()
        self._adjustment_generation += 1
        self._adjustment_timer.stop()
        self._pending_adjustments = None
        for worker in self._adjustment_workers.values():
            worker.cancel()
        self.cancel_pending_load()
        self.preview.clear()
        self.preview.setText("No image loaded")
        self.preview_availability_changed.emit(False)
        self.info.setText("Load a PNG, JPEG, TIFF, or BMP image.")
        self.histogram.set_image(None)
        self._heightfield_preview = None
        self._procedural_preview = None
        self.source_mode.blockSignals(True)
        self.source_mode.setCurrentIndex(0)
        self.source_mode.blockSignals(False)
        self._source_mode_changed(0, refresh=False)
        self.grayscale_button.setEnabled(False)
        self.invert_button.setEnabled(False)
        self._restore_controls()

    def _cancel_external_import(self) -> None:
        self._external_import_generation += 1
        if self._external_import_worker is not None:
            self._external_import_worker.cancel()
            self._external_import_worker = None

    def _restore_controls(self) -> None:
        defaults = {"Black point": 0.0, "Gamma": 1.0, "White point": 1.0,
                    "Output black": 0.0, "Output white": 1.0, "Brightness": 0.0,
                    "Contrast": 1.0, "Blur": 0.0, "Sharpen": 0.0, "Threshold": 0.5}
        for name, default in defaults.items():
            control = self.controls[name]
            control.blockSignals(True)
            control.setValue(float(self.state.adjustment_settings.get(name, default)))
            control.blockSignals(False)
        for widget, value in ((self.threshold_enabled, bool(self.state.adjustment_settings.get("threshold_enabled", False))),
                              (self.linear_light, bool(self.state.adjustment_settings.get("linear_light", False)))):
            widget.blockSignals(True)
            widget.setChecked(value)
            widget.blockSignals(False)
        self.curve_interpolation.blockSignals(True)
        self.curve_interpolation.setCurrentText("Smoothstep" if self.state.adjustment_settings.get("Curve interpolation") == "smoothstep" else "Linear")
        self.curve_interpolation.blockSignals(False)
        self.curve_editor.points = list(self.state.curve_points)
        self.curve_editor.update()
        for widget, value in zip(self.crop_controls, self.state.crop_margins):
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)
        self.resize_enabled.blockSignals(True)
        self.resize_enabled.setChecked(self.state.image_resize is not None)
        self.resize_enabled.blockSignals(False)
        for widget, value in zip((self.resize_width, self.resize_height), self.state.image_resize or (512, 512)):
            widget.blockSignals(True)
            widget.setValue(value)
            widget.setEnabled(self.state.image_resize is not None)
            widget.blockSignals(False)

    def refresh_from_state(self) -> None:
        """Refresh the preview and controls after project loading."""
        if self.state.source_type != "image":
            index = {"fractal_noise": 1, "wave_interference": 2, "mandelbrot": 3, "voronoi": 4, "ridged_noise": 5, "warped_noise": 6, "sdf": 7, "chladni": 8, "spectral": 9, "reaction_diffusion": 10, "phyllotaxis": 11, "cellular_automata": 12, "flow_field": 13, "erosion": 14, "lsystem": 15, "cracks": 16, "penrose": 17, "truchet": 18, "superformula": 19, "gaussian_peaks": 20, "julia": 21, "moire": 22, "gabor": 23, "qfractalnow_config": 24}.get(self.state.source_type, 0)
            self._restore_procedural_controls(self.state.source_descriptor)
            self._restore_composition_controls()
            self.source_mode.blockSignals(True)
            self.source_mode.setCurrentIndex(index)
            self.source_mode.blockSignals(False)
            self._source_mode_changed(index, refresh=False)
            self._procedural_preview = None
            self.info.setText(f"Procedural source: {self.state.source_type}")
            if self.state.source_type == "qfractalnow_config":
                self.qfractal_status.setText(f"Loaded {self.state.source_descriptor.get('parameters', {}).get('filename', 'embedded config')}; embedded in this project")
            self._update_provenance()
            return
        if self.state.source_image is None:
            return
        self.source_mode.blockSignals(True)
        self.source_mode.setCurrentIndex(0)
        self.source_mode.blockSignals(False)
        self._source_mode_changed(0, refresh=False)
        self.grayscale_button.setEnabled(True)
        self.invert_button.setEnabled(True)
        self._restore_controls()
        self.state.grayscale_image = None
        self._show_pixels(self.state.source_image)
        if self.state.source_path is not None:
            self.info.setText(f"{self.state.source_path.name}\n{self.state.image_width} × {self.state.image_height} px · {self.state.image_bit_depth}-bit")
        self._refresh_adjustments(mark_dirty=False)
        self._update_provenance()

    def load_path(self, path: str) -> None:
        """Decode and convert source pixels off the GUI thread."""
        self._load_generation += 1
        token = self._load_generation
        self.info.setText(f"Loading {Path(path).name}…")
        worker = FunctionWorker(_load_and_convert, path, self.linear_light.isChecked())
        self._load_workers[token] = worker
        worker.signals.finished.connect(lambda result, generation=token: self._load_finished(generation, result))
        worker.signals.failed.connect(lambda message, generation=token: self._load_failed(generation, message))
        self.thread_pool.start(worker)

    def cancel_pending_load(self) -> None:
        """Ignore results from image loads started for a previous project."""
        self._load_generation += 1

    def _load_finished(self, generation: int, result) -> None:
        self._load_workers.pop(generation, None)
        if generation != self._load_generation:
            return
        loaded, grayscale, linear_light = result
        self.state.set_source(loaded.path, loaded.pixels)
        self.source_mode.blockSignals(True)
        self.source_mode.setCurrentIndex(0)
        self.source_mode.blockSignals(False)
        self._source_mode_changed(0)
        self.grayscale_button.setEnabled(True)
        self.invert_button.setEnabled(True)
        self._show_pixels(loaded.pixels)
        self.preview_availability_changed.emit(True)
        self.info.setText(f"{loaded.path.name}\n{loaded.width} × {loaded.height} px · {loaded.bit_depth}-bit")
        geometry_default = self.state.crop_margins == (0, 0, 0, 0) and self.state.image_resize is None
        self.state.grayscale_image = grayscale if geometry_default and linear_light == self.linear_light.isChecked() else None
        self.image_loaded.emit(str(loaded.path))
        self._refresh_adjustments()

    def _load_failed(self, generation: int, message: str) -> None:
        self._load_workers.pop(generation, None)
        if generation == self._load_generation:
            self.info.setText("Could not load image.")
            self.error_occurred.emit(message)

    def _apply_grayscale(self) -> None:
        if self.state.source_image is None:
            return
        self.state.grayscale_image = None
        self.state.dirty = True
        self._refresh_adjustments()

    def _geometry_changed(self, *args) -> None:
        sender = self.sender()
        for first, second in ((0, 2), (1, 3)):
            a, b = self.crop_controls[first], self.crop_controls[second]
            if a.value() + b.value() >= 100:
                other = b if sender is a else a
                edited = a if sender is a else b
                other.blockSignals(True)
                other.setValue(99 - edited.value())
                other.blockSignals(False)
        self.state.crop_margins = tuple(control.value() for control in self.crop_controls)
        enabled = self.resize_enabled.isChecked()
        self.resize_width.setEnabled(enabled)
        self.resize_height.setEnabled(enabled)
        self.state.image_resize = (self.resize_width.value(), self.resize_height.value()) if enabled else None
        self.state.grayscale_image = None
        self.image_geometry_changed.emit()
        self._refresh_adjustments()

    def _apply_invert(self) -> None:
        if self.state.source_image is not None:
            self.state.inverted = not self.state.inverted
            self.state.dirty = True
            self._refresh_adjustments()

    def _histogram_markers_changed(self, black_point: float, white_point: float) -> None:
        """Synchronize histogram markers with the Levels controls."""
        self.controls["Black point"].blockSignals(True)
        self.controls["White point"].blockSignals(True)
        self.controls["Black point"].setValue(black_point)
        self.controls["White point"].setValue(white_point)
        self.controls["Black point"].blockSignals(False)
        self.controls["White point"].blockSignals(False)
        self._refresh_adjustments()

    def _refresh_adjustments(self, *args, mark_dirty: bool = True) -> None:
        if self.state.source_image is None:
            return
        settings = {name: control.value() for name, control in self.controls.items()}
        settings["threshold_enabled"] = self.threshold_enabled.isChecked()
        settings["linear_light"] = self.linear_light.isChecked()
        settings["Curve interpolation"] = self.curve_interpolation.currentText().lower()
        settings["inverted"] = self.state.inverted
        self.histogram.set_markers(settings["Black point"], settings["White point"])
        points = list(self.curve_editor.points)
        self.state.adjustment_settings = settings
        self.state.curve_points = points
        self._adjustment_generation += 1
        generation = self._adjustment_generation
        for worker in self._adjustment_workers.values():
            worker.cancel()
        self.state.adjusted_image = None
        self.processing_started.emit()
        if mark_dirty:
            self.state.dirty = True
            self.parameters_changed.emit()
        self._pending_adjustments = (generation, self.state.source_image, self.state.grayscale_image, settings, points, self.state.crop_margins, self.state.image_resize)
        self._adjustment_timer.start()

    def _launch_adjustments(self) -> None:
        if self._pending_adjustments is None:
            return
        generation, source, grayscale, settings, points, margins, resize = self._pending_adjustments
        self._pending_adjustments = None
        worker = FunctionWorker(_process_adjustments, source, grayscale, settings, points, self._adjustment_cache, margins, resize, inject_control=True)
        self._adjustment_workers[generation] = worker
        worker.signals.finished.connect(lambda image, token=generation: self._adjustments_finished(token, image))
        worker.signals.failed.connect(lambda message, token=generation: self._adjustments_failed(token, message))
        worker.signals.cancelled.connect(lambda token=generation: self._adjustment_workers.pop(token, None))
        self.thread_pool.start(worker)
        if grayscale is not None:
            self.gpu_adjustment_requested.emit(generation, grayscale, settings, points)

    def _adjustments_finished(self, generation: int, result) -> None:
        self._adjustment_workers.pop(generation, None)
        if generation != self._adjustment_generation:
            return
        grayscale, image = result
        self.state.grayscale_image = grayscale
        self.state.adjusted_image = image
        self.adjusted_image_ready.emit()
        self.histogram.set_image(image)
        self._refresh_preview()

    def _adjustments_failed(self, generation: int, message: str) -> None:
        self._adjustment_workers.pop(generation, None)
        if generation == self._adjustment_generation:
            self.error_occurred.emit(f"Adjustment processing failed: {message}")

    def _reset_adjustments(self) -> None:
        self.state.adjustment_settings = {}
        self.state.inverted = False
        self.state.curve_points = [(0.0, 0.0), (1.0, 1.0)]
        self._restore_controls()
        self.state.grayscale_image = None
        self._refresh_adjustments()

    def _show_pixels(self, pixels: np.ndarray) -> None:
        height, width = pixels.shape[:2]
        scale = min(1.0, 1024 / max(height, width))
        if scale < 1.0:
            pixels = cv2.resize(pixels, (max(1, round(width * scale)), max(1, round(height * scale))), interpolation=cv2.INTER_AREA)
        if pixels.dtype == np.uint16:
            pixels = (pixels.astype(np.float32) / 257.0).clip(0, 255).astype(np.uint8)
        elif pixels.dtype != np.uint8:
            raise ValueError(f"Preview requires 8-bit or 16-bit pixels; got {pixels.dtype}")
        if pixels.ndim == 2:
            image = QImage(pixels.data, pixels.shape[1], pixels.shape[0], pixels.strides[0], QImage.Format.Format_Grayscale8)
        elif pixels.shape[2] == 4:
            rgba = cv2.cvtColor(pixels, cv2.COLOR_BGRA2RGBA)
            image = QImage(rgba.data, rgba.shape[1], rgba.shape[0], rgba.strides[0], QImage.Format.Format_RGBA8888)
        else:
            rgb = cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB)
            image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format.Format_RGB888)
        self.preview.setPixmap(QPixmap.fromImage(image.copy()).scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def _show_normalized(self, image: np.ndarray) -> None:
        height, width = image.shape
        scale = min(1.0, 1024 / max(height, width))
        if scale < 1.0:
            image = cv2.resize(image, (max(1, round(width * scale)), max(1, round(height * scale))), interpolation=cv2.INTER_AREA)
        pixels = np.clip(image * 255.0, 0, 255).astype(np.uint8)
        self._show_pixels(pixels)

    def set_heightfield_preview(self, image) -> None:
        self._heightfield_preview = image
        if image is not None:
            self.preview_availability_changed.emit(True)
        if self.preview_mode.currentIndex() == 2:
            self._refresh_preview()

    def set_procedural_preview(self, image) -> None:
        self._procedural_preview = image
        if image is not None:
            self.preview_availability_changed.emit(True)
        if self.preview_mode.currentIndex() == 0 and self.is_procedural:
            self._refresh_preview()

    def _refresh_preview(self, *args) -> None:
        mode = self.preview_mode.currentIndex()
        if mode == 1 and self.state.source_image is not None:
            self._show_pixels(self.state.source_image)
        elif mode == 0 and self.is_procedural and self._procedural_preview is not None:
            self._show_normalized(self._procedural_preview)
        elif mode == 0 and self.state.adjusted_image is not None:
            self._show_normalized(self.state.adjusted_image)
        elif mode == 2 and self._heightfield_preview is not None:
            image = self._heightfield_preview
            lo, hi = float(image.min()), float(image.max())
            normalized = (image - lo) / (hi - lo) if hi > lo else np.zeros_like(image)
            self._show_normalized(normalized)
        else:
            self.preview.setText("Preview unavailable")
