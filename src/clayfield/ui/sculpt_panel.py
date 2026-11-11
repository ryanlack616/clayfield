"""Compact sculpt brush controls shown over the 3D viewport.

The panel only builds :class:`BrushSettings`; it never touches geometry. The main
window owns the session and the heightfield, so the panel stays a pure settings
widget and the sculpt math remains independently testable.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from clayfield.sculpt.brush import ALGORITHMS, BrushSettings
from clayfield.sculpt.falloff import FALLOFFS


class SculptPanel(QFrame):
    """Brush settings overlay with an enable toggle."""

    sculpt_toggled = Signal(bool)
    settings_changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("canvasOverlay")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "QFrame#canvasOverlay { background-color: #14171a; border: 1px solid #3d464e; }QLabel { color: #c8d2db; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        header = QHBoxLayout()
        header.addWidget(QLabel("SCULPT / SMOOTH"))
        header.addStretch()
        layout.addLayout(header)

        self.enable = QComboBox()
        self.enable.addItems(("Off", "On"))
        self.enable.setToolTip("Route left-drag to the smoothing brush")
        self.enable.currentTextChanged.connect(lambda text: self.sculpt_toggled.emit(text == "On"))
        layout.addLayout(self._row("Brush", self.enable))

        self.radius = QDoubleSpinBox()
        self.radius.setRange(0.5, 200.0)
        self.radius.setSingleStep(0.5)
        self.radius.setDecimals(2)
        self.radius.setSuffix(" mm")
        self.radius.setValue(5.0)
        layout.addLayout(self._row("Radius", self.radius))

        self.strength = QDoubleSpinBox()
        self.strength.setRange(0.01, 1.0)
        self.strength.setSingleStep(0.05)
        self.strength.setDecimals(2)
        self.strength.setValue(0.35)
        layout.addLayout(self._row("Strength", self.strength))

        self.falloff = QComboBox()
        self.falloff.addItems(FALLOFFS)
        self.falloff.setCurrentText("smoothstep")
        layout.addLayout(self._row("Falloff", self.falloff))

        self.algorithm = QComboBox()
        self.algorithm.addItems(ALGORITHMS)
        self.algorithm.setCurrentText("laplacian")
        layout.addLayout(self._row("Algorithm", self.algorithm))

        for widget in (self.radius, self.strength):
            widget.valueChanged.connect(self._emit_settings)
        for widget in (self.falloff, self.algorithm):
            widget.currentTextChanged.connect(self._emit_settings)
        self.setFixedWidth(250)

    def _row(self, label: str, widget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        caption = QLabel(label)
        caption.setFixedWidth(70)
        row.addWidget(caption)
        row.addWidget(widget, 1)
        return row

    def _emit_settings(self, *_args) -> None:
        self.settings_changed.emit(self.settings())

    def settings(self) -> BrushSettings:
        """Return the current brush configuration."""
        settings = BrushSettings(
            radius_mm=float(self.radius.value()),
            strength=float(self.strength.value()),
            falloff=str(self.falloff.currentText()),
            algorithm=str(self.algorithm.currentText()),
        )
        settings.validate()
        return settings
