"""Cross-section inspection dialog."""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QComboBox, QDialog, QFormLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from clayfield.terrain.cross_section import extract_profile


class ProfilePlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.distance = []
        self.values = []
        self.setMinimumSize(420, 260)

    def set_profile(self, distance, values):
        self.distance = list(distance)
        self.values = list(values)
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().base())
        if len(self.values) < 2:
            return
        margin = 28
        plot = self.rect().adjusted(margin, margin, -margin, -margin)
        low, high = min(self.values), max(self.values)
        if high <= low:
            high = low + 1.0
        painter.setPen(QPen(self.palette().mid().color(), 1))
        painter.drawRect(plot)
        painter.setPen(QPen(self.palette().highlight().color(), 2))
        points = []
        for distance, value in zip(self.distance, self.values):
            x = plot.left() + (distance - self.distance[0]) / max(1e-6, self.distance[-1] - self.distance[0]) * plot.width()
            y = plot.bottom() - (value - low) / (high - low) * plot.height()
            points.append(QPointF(x, y))
        for first, second in zip(points, points[1:]):
            painter.drawLine(first, second)


class CrossSectionDialog(QDialog):
    def __init__(self, heightfield, width_mm, depth_mm, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cross-section")
        self.resize(520, 430)
        self.heightfield = heightfield
        self.width_mm = width_mm
        self.depth_mm = depth_mm
        self.axis = QComboBox()
        self.axis.addItem("Width (X)", "width")
        self.axis.addItem("Depth (Z)", "depth")
        self.index = QSpinBox()
        self.plot = ProfilePlot()
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        form = QFormLayout()
        form.addRow("Profile direction", self.axis)
        form.addRow("Sample index", self.index)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.plot)
        layout.addWidget(self.summary)
        self.axis.currentIndexChanged.connect(self._sync_range)
        self.index.valueChanged.connect(self._update_profile)
        self._sync_range()

    def _sync_range(self):
        axis = self.axis.currentData()
        limit = self.heightfield.shape[0] if axis == "width" else self.heightfield.shape[1]
        self.index.setRange(0, max(0, limit - 1))
        self.index.setValue(limit // 2)
        self._update_profile()

    def _update_profile(self):
        axis = self.axis.currentData()
        distance, values = extract_profile(self.heightfield, self.width_mm, self.depth_mm, axis, self.index.value())
        self.plot.set_profile(distance, values)
        self.summary.setText(
            f"Distance: {float(distance[0]):.2f} to {float(distance[-1]):.2f} mm\n"
            f"Height: {float(values.min()):.2f} to {float(values.max()):.2f} mm\n"
            f"Range: {float(values.max() - values.min()):.2f} mm"
        )
