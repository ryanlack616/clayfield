"""A slider, exact-value control, and per-parameter reset button."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QSlider, QToolButton, QWidget


def parameter_row(spin, label: str) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    factor = 10 ** spin.decimals() if isinstance(spin, QDoubleSpinBox) else 1
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(round(spin.minimum() * factor), round(spin.maximum() * factor))
    slider.setValue(round(spin.value() * factor))
    slider.setMinimumWidth(55)
    slider.setToolTip(f"Adjust {label}; use the adjacent field for an exact value.")
    spin.setToolTip(f"Enter an exact value for {label}.")
    default = spin.value()
    reset = QToolButton()
    reset.setObjectName("resetButton")
    reset.setText("↺")
    reset.setToolTip(f"Reset {label} to {default}.")
    reset.setAccessibleName(f"Reset {label}")
    reset.clicked.connect(lambda: spin.setValue(default))
    slider.valueChanged.connect(lambda value: spin.setValue(value / factor if factor != 1 else value))

    def sync_slider(value):
        slider.blockSignals(True)
        slider.setValue(round(value * factor))
        slider.blockSignals(False)

    spin.valueChanged.connect(sync_slider)
    layout.addWidget(slider, 1)
    layout.addWidget(spin)
    layout.addWidget(reset)
    return row
