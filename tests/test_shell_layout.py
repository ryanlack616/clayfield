"""Shell-level behaviour: the dock layout that replaced the splitter.

These tests assert the container, not the rendering. The viewport instance is
the thing Phase 1 must not disturb, so the first test pins its identity across
the move into the dock shell.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QDockWidget, QScrollArea, QSplitter, QTabWidget

from clayfield.ui.main_window import MainWindow
from clayfield.ui.viewport import Viewport


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def make_window(monkeypatch, settings):
    """Build windows against one settings store so persistence can be observed."""
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("clayfield.ui.main_window.find_recovery_snapshots", lambda: [])
    monkeypatch.setattr("clayfield.ui.main_window.QSettings", lambda *args: settings)
    built = []

    def build():
        window = MainWindow()
        window.terrain_panel.resolution.setValue(32)
        built.append(window)
        app.processEvents()
        return window, app

    yield build
    for window in built:
        window.state.dirty = False
        window.close()
    app.processEvents()


def test_viewport_stays_central_and_docks_flank_it(make_window):
    """The splitter is gone; the viewport instance survives the move."""
    window, app = make_window()
    app.processEvents()

    assert isinstance(window.centralWidget(), Viewport)
    assert window.centralWidget() is window.viewport
    assert window.findChildren(QSplitter) == []
    assert window.findChildren(QTabWidget) == []

    assert window.dockWidgetArea(window.source_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    assert window.dockWidgetArea(window.settings_dock) == Qt.DockWidgetArea.RightDockWidgetArea


def test_docks_are_movable_floatable_and_closable(make_window):
    """A splitter pane cannot do any of these, which is why the shell moved."""
    window, app = make_window()
    app.processEvents()

    wanted = (
        QDockWidget.DockWidgetFeature.DockWidgetMovable
        | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        | QDockWidget.DockWidgetFeature.DockWidgetClosable
    )
    for dock in (window.source_dock, window.settings_dock):
        assert dock.features() & wanted == wanted
        assert isinstance(dock.widget(), type(dock.widget()))
        assert dock.objectName() in {"sourceDock", "settingsDock"}


def test_dock_panels_are_the_existing_widgets(make_window):
    """The docks hold the live panels, not copies of them."""
    window, app = make_window()
    app.processEvents()

    def scroll_of(panel):
        widget = panel.parentWidget()
        while widget is not None:
            if isinstance(widget, QScrollArea):
                return widget
            widget = widget.parentWidget()
        return None

    assert scroll_of(window.image_panel) is window.source_dock.widget()
    assert scroll_of(window.terrain_panel) is window.settings_dock.widget()


def test_one_dock_can_be_tabbed_onto_the_other(make_window):
    """Tabifiable means Qt's tab group works, not just that the flag is set."""
    window, app = make_window()
    app.processEvents()

    window.tabifyDockWidget(window.source_dock, window.settings_dock)
    app.processEvents()

    assert window.settings_dock in window.tabifiedDockWidgets(window.source_dock)
    # A tab group hides all but the active dock; Reset Layout has to un-tab it.
    window._reset_layout()
    app.processEvents()

    assert window.settings_dock not in window.tabifiedDockWidgets(window.source_dock)
    assert window.dockWidgetArea(window.source_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    assert window.dockWidgetArea(window.settings_dock) == Qt.DockWidgetArea.RightDockWidgetArea
    assert not window.settings_dock.isHidden()


def test_reset_layout_returns_both_docks_to_default_areas(make_window):
    """Reset Layout undoes a user rearrangement."""
    window, app = make_window()
    app.processEvents()

    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, window.source_dock)
    app.processEvents()
    assert window.dockWidgetArea(window.source_dock) == Qt.DockWidgetArea.RightDockWidgetArea

    window._reset_layout()
    app.processEvents()

    assert window.dockWidgetArea(window.source_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    assert window.dockWidgetArea(window.settings_dock) == Qt.DockWidgetArea.RightDockWidgetArea


def test_layout_persists_across_a_restart(make_window, settings):
    """A closed dock and a moved dock both survive a new window."""
    first, app = make_window()
    first.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, first.source_dock)
    first.settings_dock.setVisible(False)
    app.processEvents()
    first._save_dock_layout()
    saved = settings.value("dock_layout")
    assert saved
    first.state.dirty = False
    first.close()
    app.processEvents()

    second, app = make_window()
    app.processEvents()

    assert second.dockWidgetArea(second.source_dock) == Qt.DockWidgetArea.RightDockWidgetArea
    assert second.settings_dock.isHidden()


def test_reset_layout_forgets_the_saved_arrangement(make_window, settings):
    """After a reset, a restart opens in the default arrangement, not the old one."""
    first, app = make_window()
    first.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, first.source_dock)
    app.processEvents()
    first._reset_layout()
    app.processEvents()
    first.state.dirty = False
    first.close()
    app.processEvents()

    second, app = make_window()
    app.processEvents()

    assert second.dockWidgetArea(second.source_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    # isVisible() is false while the window itself has not been shown; the
    # explicit hidden flag is what a saved layout restores.
    assert not second.settings_dock.isHidden()


def test_default_size_is_the_spec_size(make_window):
    """GUI_LAYOUT.md asks for 1600 x 1000; the floor is smaller than that."""
    window, app = make_window()
    app.processEvents()

    assert (window.width(), window.height()) == (1600, 1000)
    assert window.minimumSizeHint().width() <= 1600
