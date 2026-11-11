"""Compact sculpt brush controls shown over the 3D viewport.

The panel only builds :class:`BrushSettings`; it never touches geometry. The main
window owns the session and the heightfield, so the panel stays a pure settings
widget and the sculpt math remains independently testable.

The brush smooths the surface; it does not raise or lower it. The header says so
because "sculpt" alone leads users to expect an additive tool that this release
does not ship.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
)

from clayfield.sculpt.brush import ALGORITHMS, BrushSettings
from clayfield.sculpt.falloff import FALLOFFS

_PANEL_STYLE = (
    "QFrame#canvasOverlay { background-color: #14171a; border: 1px solid #3d464e; }"
    "QLabel { color: #c8d2db; }"
    "QLabel#sculptHint { color: #7d8b98; }"
)


class SculptPanel(QFrame):
    """Brush settings overlay with an enable toggle and a close button."""

    sculpt_toggled = Signal(bool)
    settings_changed = Signal(object)
    closed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("canvasOverlay")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(_PANEL_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)
        header = QHBoxLayout()
        title = QLabel("SCULPT BRUSH")
        title.setToolTip(
            "Smoothing brush over the sculpt layer. It evens out the surface and does not raise or lower it."
        )
        self.close_button = QToolButton()
        self.close_button.setText("×")
        self.close_button.setAutoRaise(True)
        # The light theme paints a dark glyph, which disappears on this dark card.
        self.close_button.setStyleSheet(
            "QToolButton { color: #c8d2db; background: transparent; border: none; padding: 0 4px; }"
            "QToolButton:hover { color: #ffffff; }"
        )
        self.close_button.setToolTip("Hide the brush controls (View → Sculpt Brush shows them again)")
        self.close_button.clicked.connect(lambda: self.closed.emit())
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.close_button)
        layout.addLayout(header)

        hint = QLabel("Smooths only — no raise/lower")
        hint.setObjectName("sculptHint")
        layout.addWidget(hint)

        self.enable = QComboBox()
        self.enable.addItems(("Off", "On"))
        self.enable.setToolTip(
            "Route left-drag to the smoothing brush. Right-drag orbits and middle-drag pans while it is on."
        )
        self.enable.currentTextChanged.connect(lambda text: self.sculpt_toggled.emit(text == "On"))
        layout.addLayout(self._row("Brush", self.enable))

        self.radius = QDoubleSpinBox()
        self.radius.setRange(0.5, 200.0)
        self.radius.setSingleStep(0.5)
        self.radius.setDecimals(2)
        self.radius.setSuffix(" mm")
        self.radius.setValue(5.0)
        self.radius.setToolTip("Brush footprint radius in millimetres; the viewport ring shows it")
        layout.addLayout(self._row("Radius", self.radius))

        self.strength = QDoubleSpinBox()
        self.strength.setRange(0.01, 1.0)
        self.strength.setSingleStep(0.05)
        self.strength.setDecimals(2)
        self.strength.setValue(0.35)
        self.strength.setToolTip("Fraction of the full smoothing applied per dab; 1.0 is strongest")
        layout.addLayout(self._row("Strength", self.strength))

        self.falloff = QComboBox()
        self.falloff.addItems(FALLOFFS)
        self.falloff.setCurrentText("smoothstep")
        self.falloff.setToolTip(
            "How brush influence fades from the centre to the rim. "
            "linear: straight ramp; smoothstep: soft edge; gaussian: bell curve; constant: flat"
        )
        layout.addLayout(self._row("Falloff", self.falloff))

        self.algorithm = QComboBox()
        self.algorithm.addItems(ALGORITHMS)
        self.algorithm.setCurrentText("laplacian")
        self.algorithm.setToolTip(
            "laplacian: fast, shrinks detail; taubin: keeps volume and resists shrinkage; "
            "bilateral: keeps edges and steps"
        )
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

    @property
    def enabled(self) -> bool:
        """Whether the brush is routed to left-drag."""
        return self.enable.currentText() == "On"

    def set_enabled(self, enabled: bool) -> None:
        """Reflect the brush state without emitting ``sculpt_toggled`` again."""
        text = "On" if enabled else "Off"
        if self.enable.currentText() == text:
            return
        self.enable.blockSignals(True)
        self.enable.setCurrentText(text)
        self.enable.blockSignals(False)

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
