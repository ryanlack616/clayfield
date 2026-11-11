"""Export dimensions, heightmap, and low-resolution mesh validation preview."""

import numpy as np
from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from clayfield.app.worker import FunctionWorker
from clayfield.geometry.container import ContainerSettings, container_footprint
from clayfield.geometry.estimates import estimate_solid_mesh
from clayfield.geometry.mesh_generator import generate_solid_mesh
from clayfield.geometry.validation import validate_mesh
from clayfield.terrain.fabrication import FabricationProfile, analyze_heightfield


def _validate_preview(heightfield, width, depth, base, mode):
    rows = np.linspace(0, heightfield.shape[0] - 1, min(96, heightfield.shape[0]), dtype=int)
    columns = np.linspace(0, heightfield.shape[1] - 1, min(96, heightfield.shape[1]), dtype=int)
    sample = heightfield[np.ix_(rows, columns)]
    return validate_mesh(generate_solid_mesh(sample, width, depth, base, mode))


class ExportPreviewDialog(QDialog):
    """Show approximate output before choosing a destination."""

    def __init__(self, state, label: str, parent=None, *, mesh: bool = True, final_analysis=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{label} Export Preview")
        self.resize(460, 480)
        layout = QVBoxLayout(self)
        heightfield = state.physical_heightfield
        display = -heightfield if state.relief_mode == "negative" else heightfield
        low, high = float(display.min()), float(display.max())
        span = high - low
        pixels = (
            np.rint((display - low) * (255.0 / span)).astype(np.uint8)
            if span > 0
            else np.zeros(display.shape, dtype=np.uint8)
        )
        pixels = np.ascontiguousarray(pixels)
        image = QImage(
            pixels.data, pixels.shape[1], pixels.shape[0], pixels.strides[0], QImage.Format.Format_Grayscale8
        ).copy()
        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setPixmap(
            QPixmap.fromImage(image).scaled(
                360, 240, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
        )
        layout.addWidget(preview)
        width, depth = state.terrain_width_mm, state.terrain_depth_mm
        container = ContainerSettings(
            state.container_mode,
            state.container_wall_thickness_mm,
            state.container_clearance_mm,
            state.container_outside_dimensions,
        )
        footprint_width, footprint_depth = container_footprint(width, depth, container)
        metrics = analyze_heightfield(
            display,
            width,
            depth,
            state.base_thickness_mm,
            "positive",
            profile=FabricationProfile(**state.fabrication_profile),
        )
        wall = metrics.minimum_wall_mm
        estimate = estimate_solid_mesh(state.export_resolution[1], state.export_resolution[0])
        self.summary = QLabel(
            f"Physical width × depth: {footprint_width:.2f} × {footprint_depth:.2f} mm\n"
            f"Surface range: {low:.2f} to {high:.2f} mm\n"
            f"Estimated minimum wall: {wall:.2f} mm\n"
            f"Resolved feature estimate: {metrics.minimum_resolved_feature_width_mm:.3f} mm\n"
            f"Maximum slope: {metrics.maximum_slope_degrees:.1f} degrees\n"
            + (
                f"Container: {container.mode}; walls {container.wall_thickness_mm:.2f} mm; clearance {container.clearance_above_model_mm:.2f} mm\n"
                if container.mode != "none"
                else ""
            )
            + f"Export resolution: {state.export_resolution[0]} × {state.export_resolution[1]}\n"
            + (
                f"Solid: {estimate.triangle_count:,} triangles; estimated working memory {estimate.working_mebibytes:.0f} MiB"
                if mesh
                else "Heightmap values are normalized to the exported range."
            )
            + ("\nWarnings: " + ", ".join(metrics.warnings) if metrics.warnings else "")
        )
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.final_metrics = QLabel("Final export-resolution analysis: not requested")
        self.final_metrics.setWordWrap(True)
        layout.addWidget(self.final_metrics)
        self.validation = QLabel(
            "Validating preview mesh…" if mesh else "Heightmap preview; final export uses the selected resolution."
        )
        self.validation.setWordWrap(True)
        layout.addWidget(self.validation)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Choose File…")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._worker = None
        self._analysis_worker = None
        if mesh:
            self._worker = FunctionWorker(
                _validate_preview, heightfield, width, depth, state.base_thickness_mm, state.relief_mode
            )
            self._worker.signals.finished.connect(self._validation_finished)
            self._worker.signals.failed.connect(self._validation_failed)
            QThreadPool.globalInstance().start(self._worker)
        if final_analysis is not None:
            function, args, kwargs = final_analysis
            self.final_metrics.setText("Final export-resolution analysis: calculating…")
            self._analysis_worker = FunctionWorker(function, *args, **kwargs, inject_control=True)
            self._analysis_worker.signals.progress.connect(
                lambda percent, message: self.final_metrics.setText(
                    f"Final export-resolution analysis: {percent}% — {message}"
                )
            )
            self._analysis_worker.signals.finished.connect(self._final_analysis_finished)
            self._analysis_worker.signals.failed.connect(
                lambda message: self.final_metrics.setText(f"Final export-resolution analysis failed: {message}")
            )
            QThreadPool.globalInstance().start(self._analysis_worker)

    def _validation_finished(self, report) -> None:
        self._worker = None
        self.validation.setText(
            f"Sampled preview validation: {report.message}. Final export is validated independently."
        )

    def _validation_failed(self, message: str) -> None:
        self._worker = None
        self.validation.setText(f"Preview validation failed: {message}")

    def _final_analysis_finished(self, metrics) -> None:
        self._analysis_worker = None
        warnings = ", ".join(metrics.warnings) if metrics.warnings else "none"
        self.final_metrics.setText(
            f"Final export field: wall {metrics.minimum_wall_mm:.2f} mm; "
            f"resolved feature {metrics.minimum_resolved_feature_width_mm:.3f} mm; "
            f"maximum slope {metrics.maximum_slope_degrees:.1f} degrees; "
            f"warnings: {warnings}"
        )
