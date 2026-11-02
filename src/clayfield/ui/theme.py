"""Application-wide light and dark Qt Fusion palettes."""

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def apply_theme(dark: bool) -> None:
    app = QApplication.instance()
    if app is None:
        return
    app.setStyle("Fusion")
    app.setStyleSheet(
        """
        QComboBox, QLineEdit { min-height: 28px; padding: 2px 6px; }
        QSpinBox, QDoubleSpinBox { min-height: 28px; padding: 2px 34px 2px 10px; }
        QSpinBox::up-button, QDoubleSpinBox::up-button {
            subcontrol-origin: border;
            subcontrol-position: right center;
            width: 20px;
            height: 20px;
        }
        QSpinBox::down-button, QDoubleSpinBox::down-button {
            subcontrol-origin: border;
            subcontrol-position: right center;
            right: 20px;
            width: 20px;
            height: 20px;
        }
        QPushButton { min-height: 30px; padding: 2px 10px; }
        QCheckBox { min-height: 26px; spacing: 7px; }
        QToolButton { min-height: 26px; padding: 2px 8px; }
        QToolButton#resetButton { min-height: 24px; padding: 1px 7px; }
        QToolButton#sectionButton { font-size: 13pt; font-weight: 500; }
        QMenuBar { min-height: 34px; }
        QMenuBar::item { padding: 8px 12px; }
        QSlider::groove:horizontal { height: 5px; }
        QSlider::handle:horizontal { width: 8px; height: 20px; margin: -8px 0; border-radius: 2px; background: #6ea6cc; border: 1px solid #9bc5df; }
        """
    )
    if not dark:
        app.setPalette(app.style().standardPalette())
        return
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: "#25292e",
        QPalette.ColorRole.WindowText: "#edf0f2",
        QPalette.ColorRole.Base: "#181b1f",
        QPalette.ColorRole.AlternateBase: "#30363d",
        QPalette.ColorRole.ToolTipBase: "#353c44",
        QPalette.ColorRole.ToolTipText: "#ffffff",
        QPalette.ColorRole.Text: "#edf0f2",
        QPalette.ColorRole.Button: "#343a42",
        QPalette.ColorRole.ButtonText: "#edf0f2",
        QPalette.ColorRole.BrightText: "#ff6666",
        QPalette.ColorRole.Highlight: "#4689bd",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.Link: "#79bbec",
    }
    for role, value in colors.items():
        palette.setColor(role, QColor(value))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#8a9299"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#8a9299"))
    app.setPalette(palette)
