"""Small interactive tone-curve editor."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QMenu, QWidget


class CurveEditor(QWidget):
    """Edit normalized tone-curve control points by mouse."""

    curve_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.points: list[tuple[float, float]] = [(0.0, 0.0), (1.0, 1.0)]
        self.active = -1
        self.setMinimumSize(180, 180)
        self.setMouseTracking(True)

    def reset(self) -> None:
        self.points = [(0.0, 0.0), (1.0, 1.0)]
        self.active = -1
        self.curve_changed.emit(self.points)
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().base())
        pen = QPen(self.palette().mid().color())
        painter.setPen(pen)
        for fraction in (0.25, 0.5, 0.75):
            x = int(fraction * self.width())
            y = int(fraction * self.height())
            painter.drawLine(x, 0, x, self.height())
            painter.drawLine(0, y, self.width(), y)
        painter.setPen(QPen(self.palette().mid().color(), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, self.height(), self.width(), 0)
        painter.setPen(QPen(self.palette().highlight().color(), 2))
        previous = None
        for index in range(self.width() + 1):
            x = index / max(1, self.width())
            y = self._interpolated(x)
            point = QPointF(index, (1.0 - y) * self.height())
            if previous is not None:
                painter.drawLine(previous, point)
            previous = point
        painter.setPen(QPen(self.palette().text().color(), 2))
        for x, y in self.points:
            painter.drawEllipse(QPointF(x * self.width(), (1.0 - y) * self.height()), 4, 4)

    def mousePressEvent(self, event) -> None:
        point = self._normalized(event.position())
        distances = [((x - point[0]) ** 2 + (y - point[1]) ** 2, i) for i, (x, y) in enumerate(self.points)]
        nearest = min(distances)[1] if distances and min(distances)[0] < 0.01 else -1
        if event.button() == Qt.MouseButton.RightButton:
            menu = QMenu(self)
            delete_action = menu.addAction("Delete selected point")
            delete_action.setEnabled(0 < nearest < len(self.points) - 1)
            delete_action.triggered.connect(lambda: self._delete_point(nearest))
            menu.addSeparator()
            for label, preset in ((
                ("Linear", [(0.0, 0.0), (1.0, 1.0)]),
                ("S-curve", [(0.0, 0.0), (0.25, 0.1), (0.5, 0.5), (0.75, 0.9), (1.0, 1.0)]),
                ("Lift shadows", [(0.0, 0.2), (0.5, 0.6), (1.0, 1.0)]),
                ("Lower highlights", [(0.0, 0.0), (0.5, 0.4), (1.0, 0.8)]),
            )):
                action = menu.addAction(label)
                action.triggered.connect(lambda checked=False, points=preset: self._set_preset(points))
            menu.exec(event.globalPosition().toPoint())
            return
        if nearest >= 0:
            self.active = nearest
        elif event.button() == Qt.MouseButton.LeftButton:
            self.points.append(point)
            self.points.sort()
            self.active = self.points.index(point)
            self.curve_changed.emit(self.points)
        self.update()

    def _delete_point(self, index: int) -> None:
        """Delete an interior point while preserving the curve endpoints."""
        if 0 < index < len(self.points) - 1:
            self.points.pop(index)
            self.active = -1
            self.curve_changed.emit(self.points)
            self.update()

    def _set_preset(self, points: list[tuple[float, float]]) -> None:
        """Apply a normalized, stable preset curve."""
        self.points = list(points)
        self.active = -1
        self.curve_changed.emit(self.points)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self.active < 0:
            return
        x, y = self._normalized(event.position())
        if self.active == 0:
            x = 0.0
        elif self.active == len(self.points) - 1:
            x = 1.0
        else:
            x = max(self.points[self.active - 1][0] + 0.005, min(self.points[self.active + 1][0] - 0.005, x))
        self.points[self.active] = (x, y)
        self.points.sort()
        self.active = self.points.index((x, y))
        self.curve_changed.emit(self.points)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        del event
        self.active = -1

    def _normalized(self, position: QPointF) -> tuple[float, float]:
        return (max(0.0, min(1.0, position.x() / max(1, self.width()))), max(0.0, min(1.0, 1.0 - position.y() / max(1, self.height()))))

    def _interpolated(self, x: float) -> float:
        # strict=False: adjacent-pair iteration is shorter by one by design.
        for left, right in zip(self.points, self.points[1:], strict=False):
            if left[0] <= x <= right[0]:
                fraction = (x - left[0]) / max(1e-6, right[0] - left[0])
                return left[1] + fraction * (right[1] - left[1])
        return self.points[-1][1]
