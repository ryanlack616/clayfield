"""Small viewport orientation indicator."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QMatrix4x4, QPainter, QPen, QVector3D
from PySide6.QtWidgets import QWidget


class AxisGizmo(QWidget):
    """Draw a compact XYZ orientation helper over the 3D viewport."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(112, 96)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._view_matrix = QMatrix4x4()

    def set_view_matrix(self, matrix: QMatrix4x4) -> None:
        """Update the projected axis directions from the active camera."""
        self._view_matrix = QMatrix4x4(matrix)
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        origin = QPointF(50, 58)
        axes = (
            (QVector3D(1, 0, 0), QColor("#db5b5b"), "X"),
            (QVector3D(0, 1, 0), QColor("#66c47a"), "Y"),
            (QVector3D(0, 0, 1), QColor("#5e9ee8"), "Z"),
        )
        for axis, color, label in axes:
            projected = self._view_matrix.mapVector(axis)
            endpoint = origin + QPointF(projected.x() * 34.0, -projected.y() * 34.0)
            painter.setPen(QPen(color, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(origin, endpoint)
            painter.setPen(QPen(color, 1))
            painter.drawText(endpoint + QPointF(-4, -5), label)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#d9e0e5"))
        painter.drawEllipse(origin, 3, 3)
