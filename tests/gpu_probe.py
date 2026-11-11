"""Run GPU/CPU agreement checks in an actual Qt OpenGL context."""

import sys
import traceback

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication

from clayfield.app.application import configure_opengl
from clayfield.image.pipeline import apply_adjustments
from clayfield.ui.gpu_pipeline import GpuImagePipeline


class Probe(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self.passed = False

    def initializeGL(self):
        try:
            rng = np.random.default_rng(3)
            image = rng.random((45, 71), dtype=np.float32)
            image[0, :3] = [0.0, 0.5, 1.0]
            points = [(0.0, 0.0), (0.35, 0.2), (0.8, 0.95), (1.0, 1.0)]
            cases = [
                {},
                {
                    "Black point": 0.12,
                    "White point": 0.85,
                    "Gamma": 1.4,
                    "Output black": 0.04,
                    "Output white": 0.9,
                    "Brightness": 0.1,
                    "Contrast": 1.3,
                    "inverted": True,
                    "Curve interpolation": "smoothstep",
                },
                {"threshold_enabled": True, "Threshold": 0.5, "inverted": True},
                {"Blur": 1.2},
                {"Sharpen": 1.1},
                {"Blur": 2.0, "Sharpen": 0.8, "Gamma": 1.3},
                {"Blur": 1.2, "threshold_enabled": True, "Threshold": 0.5},
                {"Blur": 20.0, "Sharpen": 0.5},
            ]
            pipeline = GpuImagePipeline()
            try:
                for settings in cases:
                    actual = pipeline.process(image, settings, points)
                    expected = apply_adjustments(image, settings, points)
                    np.testing.assert_allclose(actual, expected, atol=0.001, rtol=0)
                tiny = np.array([[0.0, 0.2, 1.0], [0.8, 0.5, 0.1]], dtype=np.float32)
                settings = {"Blur": 2.0, "Sharpen": 1.0}
                np.testing.assert_allclose(
                    pipeline.process(tiny, settings, points),
                    apply_adjustments(tiny, settings, points),
                    atol=0.001,
                    rtol=0,
                )
                print("GPU and CPU image adjustments agree within 0.001", flush=True)
                self.passed = True
            finally:
                pipeline.close()
        except Exception:
            traceback.print_exc()


configure_opengl()
app = QApplication([])
probe = Probe()
probe.show()
QTimer.singleShot(1000, lambda: app.exit(0 if probe.passed else 1))
sys.exit(app.exec())
