"""Height ramp colour picker for the terrain shading.

The fragment shader mixes two colours across the height range, so the editor is
just two swatches plus a preview of the mix between them. Colours are kept as
float triples in 0.0-1.0 to match what ``glUniform3f`` takes; the viewport does
not accept an invalid triple, so the same validation runs here before the dialog
can return one.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def to_qcolor(color: tuple[float, float, float]) -> QColor:
    """Convert a float RGB triple into a ``QColor``."""
    return QColor.fromRgbF(*(float(channel) for channel in color))


class ColorSwatch(QToolButton):
    """A button painted with the colour it holds; clicking opens a picker."""

    color_changed = Signal(tuple)

    def __init__(self, color: tuple[float, float, float], title: str, parent=None) -> None:
        super().__init__(parent)
        self._title = title
        self._color = to_qcolor(color)
        self.setFixedSize(96, 26)
        self.setToolTip(f"Choose the {title.lower()} colour of the height ramp")
        self.clicked.connect(self._pick)
        self._paint()

    def _pick(self) -> None:
        chosen = QColorDialog.getColor(self._color, self, self._title)
        if chosen.isValid():
            self.set_color(chosen)

    def set_color(self, color: QColor) -> None:
        """Adopt ``color`` and announce the change."""
        self._color = QColor(color)
        self._paint()
        self.color_changed.emit(self.rgb())

    def rgb(self) -> tuple[float, float, float]:
        """Return the held colour as a float triple."""
        return (self._color.redF(), self._color.greenF(), self._color.blueF())

    def _paint(self) -> None:
        pixmap = QPixmap(QSize(self.width(), self.height()))
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.fillRect(pixmap.rect(), self._color)
        # The border has to contrast with the fill, or a dark swatch reads as a
        # hole and a light one bleeds into the dialog background.
        edge = self._color.lighter(170) if self._color.lightnessF() < 0.5 else self._color.darker(170)
        painter.setPen(QPen(edge, 1))
        painter.drawRect(pixmap.rect().adjusted(0, 0, -1, -1))
        painter.end()
        self.setIcon(pixmap)
        self.setIconSize(pixmap.size())


class RampPreview(QWidget):
    """Horizontal gradient showing the mix from the low to the high colour."""

    def __init__(self, low: tuple[float, float, float], high: tuple[float, float, float], parent=None) -> None:
        super().__init__(parent)
        self._low = to_qcolor(low)
        self._high = to_qcolor(high)
        self.setMinimumHeight(26)
        self.setMinimumWidth(220)

    def set_colors(self, low: tuple[float, float, float], high: tuple[float, float, float]) -> None:
        """Replace both ends of the ramp and repaint."""
        self._low = to_qcolor(low)
        self._high = to_qcolor(high)
        self.update()

    def low(self) -> QColor:
        """Return the colour drawn at the low end."""
        return QColor(self._low)

    def high(self) -> QColor:
        """Return the colour drawn at the high end."""
        return QColor(self._high)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        gradient = QLinearGradient(0.0, 0.0, float(self.width()), 0.0)
        gradient.setColorAt(0.0, self._low)
        gradient.setColorAt(1.0, self._high)
        painter.fillRect(self.rect(), gradient)
        painter.setPen(QPen(self.palette().mid().color(), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))


class HeightColorDialog(QDialog):
    """Edit the low and high colours of the height ramp.

    ``exec()`` returning truthy means the user accepted; read the result with
    :meth:`colors` and apply it to the viewport. The dialog never touches the
    viewport itself, so it stays testable without a GL context.
    """

    def __init__(
        self,
        low: tuple[float, float, float],
        high: tuple[float, float, float],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Height Colors")
        self.low_swatch = ColorSwatch(low, "Low")
        self.high_swatch = ColorSwatch(high, "High")
        self.preview = RampPreview(low, high)
        form = QFormLayout()
        form.addRow("Low height", self.low_swatch)
        form.addRow("High height", self.high_swatch)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("Ramp preview"))
        layout.addWidget(self.preview)
        layout.addWidget(buttons)
        self.low_swatch.color_changed.connect(self._refresh_preview)
        self.high_swatch.color_changed.connect(self._refresh_preview)

    def _refresh_preview(self, *_args) -> None:
        low, high = self.colors()
        self.preview.set_colors(low, high)

    def colors(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Return ``(low, high)`` as float RGB triples."""
        return self.low_swatch.rgb(), self.high_swatch.rgb()
