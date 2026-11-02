"""Compact histogram widget for normalized grayscale data."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QSize, QPointF, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QWidget


class HistogramWidget(QWidget):
    """Draw a lightweight histogram with draggable input-level markers."""

    markers_changed = Signal(float, float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.values = np.zeros(256, dtype=np.float32)
        self.black_point = 0.0
        self.white_point = 1.0
        self._active_marker = None
        self.setMinimumSize(QSize(180, 90))

    def set_image(self, image: np.ndarray | None) -> None:
        if image is None:
            self.values.fill(0.0)
        else:
            values = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
            self.values = np.bincount((values * 255).astype(np.uint8).ravel(), minlength=256).astype(np.float32)
            peak = float(self.values.max())
            if peak:
                self.values /= peak
        self.update()

    def set_markers(self, black_point: float, white_point: float) -> None:
        """Set normalized input markers without emitting a change signal."""
        self.black_point = max(0.0, min(1.0, float(black_point)))
        self.white_point = max(self.black_point + 0.005, min(1.0, float(white_point)))
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        position = max(0.0, min(1.0, event.position().x() / max(1, self.width())))
        distances = {
            "black": abs(position - self.black_point),
            "white": abs(position - self.white_point),
        }
        nearest = min(distances, key=distances.get)
        self._active_marker = nearest if distances[nearest] * self.width() <= 10.0 else None
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._active_marker is None:
            event.ignore()
            return
        position = max(0.0, min(1.0, event.position().x() / max(1, self.width())))
        if self._active_marker == "black":
            self.black_point = min(position, self.white_point - 0.005)
        else:
            self.white_point = max(position, self.black_point + 0.005)
        self.markers_changed.emit(self.black_point, self.white_point)
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._active_marker = None
        event.accept()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        if self.values.max() == 0:
            return
        pen = QPen(self.palette().text().color())
        painter.setPen(pen)
        width = max(1, self.width() // 256)
        baseline = self.height() - 4
        for index, value in enumerate(self.values):
            height = int(value * (self.height() - 8))
            painter.drawLine(index * self.width() // 256, baseline, index * self.width() // 256, baseline - height)
        marker_pen = QPen(self.palette().highlight().color(), 2)
        painter.setPen(marker_pen)
        for marker in (self.black_point, self.white_point):
            x = int(marker * max(1, self.width() - 1))
            painter.drawLine(x, 0, x, self.height())
