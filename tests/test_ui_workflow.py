"""Exercise the image-to-terrain and project lifecycle through Qt widgets."""

import os
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import cv2
import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, QSettings, Qt
from PySide6.QtGui import QMouseEvent, QPalette
from PySide6.QtWidgets import QApplication, QDialog, QSlider, QToolButton

from clayfield.app.project_io import load_project, save_project
from clayfield.app.project_state import ProjectState
from clayfield.ui.main_window import MainWindow


@pytest.fixture
def window(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr("clayfield.ui.main_window.find_recovery_snapshots", lambda: [])
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("clayfield.ui.main_window.QSettings", lambda *args: settings)
    window = MainWindow()
    window.terrain_panel.resolution.setValue(32)
    yield window, app
    window.image_panel.thread_pool.waitForDone()
    window.thread_pool.waitForDone()
    window.state.dirty = False
    window.close()
    app.processEvents()


def wait_for(app, predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.005)
    pytest.fail("Timed out waiting for background processing")


def test_load_image_builds_terrain_and_inverts_once(window, tmp_path: Path):
    win, app = window
    source = np.array([[0, 255], [0, 255]], dtype=np.uint8)
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), source)
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    assert win.state.dirty
    np.testing.assert_allclose(win.state.physical_heightfield[0, [0, -1]], [0, 8], atol=0.01)
    win.image_panel._apply_invert()
    assert win.state.adjusted_image is None
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    np.testing.assert_allclose(win.state.physical_heightfield[0, [0, -1]], [8, 0], atol=0.01)


def test_image_primary_can_use_v2_secondary_composition(window, tmp_path: Path):
    win, app = window
    path = tmp_path / "primary.png"
    assert cv2.imwrite(str(path), np.array([[0, 255], [255, 0]], dtype=np.uint8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    original = win.state.physical_heightfield.copy()
    win.image_panel.composition_controls["enabled"].setChecked(True)
    wait_for(
        app,
        lambda: (
            win.state.physical_heightfield is not None and not np.array_equal(win.state.physical_heightfield, original)
        ),
    )
    assert win.state.source_type == "image"
    assert win.state.pipeline_snapshot is not None


def test_image_primary_composition_preserves_non_square_preview_resolution(window, tmp_path: Path):
    win, app = window
    path = tmp_path / "wide-primary.png"
    assert cv2.imwrite(str(path), np.arange(32, dtype=np.uint8).reshape(4, 8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    assert win.state.heightfield_resolution == (32, 16)

    original = win.state.physical_heightfield.copy()

    win.image_panel.composition_controls["enabled"].setChecked(True)

    wait_for(
        app,
        lambda: (
            win.state.pipeline_snapshot is not None
            and win.state.physical_heightfield is not None
            and not np.array_equal(win.state.physical_heightfield, original)
        ),
    )

    assert win.state.physical_heightfield.shape == (16, 32)


def test_image_primary_mask_composition_uses_v2_pipeline(window, tmp_path: Path):
    win, app = window
    path = tmp_path / "primary-mask.png"
    assert cv2.imwrite(str(path), np.array([[0, 255], [255, 0]], dtype=np.uint8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    original = win.state.physical_heightfield.copy()
    win.image_panel.composition_controls["enabled"].setChecked(True)
    win.image_panel.composition_controls["mask_enabled"].setChecked(True)
    wait_for(
        app,
        lambda: (
            win.state.physical_heightfield is not None and not np.array_equal(win.state.physical_heightfield, original)
        ),
    )
    assert win.state.mask_source_descriptor["type"] == "radial_mask"


def test_switching_sources_retains_image_data(window, tmp_path: Path):
    win, app = window
    path = tmp_path / "retained.png"
    source = np.array([[0, 255], [255, 0]], dtype=np.uint8)
    assert cv2.imwrite(str(path), source)
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    pixels = win.state.source_image
    win.image_panel.source_mode.setCurrentText("Fractal noise")
    wait_for(app, lambda: win.state.source_type == "fractal_noise" and win.state.physical_heightfield is not None)
    assert win.state.source_image is pixels
    win.image_panel.source_mode.setCurrentText("Image")
    wait_for(app, lambda: win.state.source_type == "image" and win.state.physical_heightfield is not None)
    np.testing.assert_array_equal(win.state.source_image, source)


def test_pattern_source_randomize_and_reset_are_undoable(window):
    win, app = window
    win.image_panel.source_mode.setCurrentText("Penrose")
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    original = win.state.source_descriptor
    win.image_panel.source_randomize.click()
    wait_for(app, lambda: win.state.physical_heightfield is not None and win.state.source_descriptor != original)
    win.image_panel.source_reset.click()
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    assert win.state.source_descriptor["parameters"]["seed"] == 0


def test_all_pattern_source_modes_build_preview(window):
    win, app = window
    modes = [
        "Fractal noise",
        "Wave interference",
        "Mandelbrot",
        "Voronoi",
        "Ridged noise",
        "Warped noise",
        "SDF shapes",
        "Chladni",
        "Spectral",
        "Reaction-diffusion",
        "Phyllotaxis",
        "Cellular automata",
        "Flow field",
        "Erosion",
        "L-system",
        "Cracks",
        "Penrose",
        "Truchet",
    ]
    for mode in modes:
        win.image_panel.source_mode.setCurrentText(mode)
        wait_for(app, lambda: win.state.physical_heightfield is not None)
        assert win.state.source_type != "image"


def test_procedural_noise_builds_terrain_without_an_image(window):
    win, app = window
    win.image_panel.source_mode.setCurrentText("Fractal noise")
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    assert win.state.source_type == "fractal_noise"
    assert win.state.source_image is None
    assert win.state.physical_heightfield.shape == (32, 32)
    first = win.state.physical_heightfield.copy()
    win.image_panel.procedural_controls["noise_seed"].setValue(9)
    wait_for(
        app,
        lambda: (
            win.state.physical_heightfield is not None and not np.array_equal(win.state.physical_heightfield, first)
        ),
    )
    assert win.image_panel._procedural_preview is not None


def test_procedural_preview_preserves_non_square_resolution(window):
    win, app = window
    win.terrain_panel.depth.setValue(50)
    win.image_panel.source_mode.setCurrentText("Fractal noise")
    wait_for(app, lambda: win.state.physical_heightfield is not None)

    assert win.state.heightfield_resolution == (32, 16)
    assert win.state.physical_heightfield.shape == (16, 32)


def test_procedural_composition_and_mask_are_persisted(window, tmp_path: Path):
    win, app = window
    win.image_panel.source_mode.setCurrentText("Fractal noise")
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    first = win.state.physical_heightfield.copy()
    win.image_panel.composition_controls["enabled"].setChecked(True)
    win.image_panel.composition_controls["mask_enabled"].setChecked(True)
    win.image_panel.composition_controls["amount"].setValue(0.8)
    wait_for(
        app,
        lambda: (
            win.state.physical_heightfield is not None and not np.array_equal(win.state.physical_heightfield, first)
        ),
    )
    assert win.state.secondary_source_descriptor is not None
    assert win.state.mask_source_descriptor is not None
    project = save_project(win.state, tmp_path / "composed.clayfield")
    restored = ProjectState()
    load_project(project, restored)
    assert restored.composition_settings["enabled"]
    assert restored.secondary_source_descriptor is not None
    assert restored.mask_source_descriptor is not None


def test_secondary_can_copy_primary_source_configuration(window):
    win, app = window
    win.image_panel.source_mode.setCurrentText("Warped noise")
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    primary = dict(win.state.source_descriptor)
    win.image_panel.composition_controls["copy_primary"].click()
    wait_for(
        app, lambda: win.state.secondary_source_descriptor is not None and win.state.physical_heightfield is not None
    )
    assert win.state.secondary_source_descriptor == primary


def test_secondary_has_independent_processing_settings(window):
    win, app = window
    win.image_panel.source_mode.setCurrentText("Fractal noise")
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    win.image_panel.composition_controls["enabled"].setChecked(True)
    win.image_panel.composition_controls["secondary_gamma"].setValue(1.8)
    win.image_panel.composition_controls["secondary_contrast"].setValue(1.5)
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    assert win.state.secondary_processing_settings["input_gamma"] == 1.8
    assert win.state.secondary_processing_settings["contrast"] == 1.5


def test_compose_section_collapses_and_expands(window):
    win, app = window
    assert not win.image_panel.compose_toggle.isChecked()
    win.image_panel.compose_toggle.click()
    assert win.image_panel.compose_toggle.isChecked()
    assert "▾" in win.image_panel.compose_toggle.text()
    win.image_panel.compose_toggle.click()
    assert not win.image_panel.compose_toggle.isChecked()
    assert "▸" in win.image_panel.compose_toggle.text()


def test_secondary_heightmap_and_mask_imports_are_composed(window, tmp_path: Path, monkeypatch):
    win, app = window
    win.image_panel.source_mode.setCurrentText("Fractal noise")
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    secondary_path = tmp_path / "secondary.png"
    mask_path = tmp_path / "mask.png"
    assert cv2.imwrite(str(secondary_path), np.array([[0, 255], [255, 0]], dtype=np.uint8))
    assert cv2.imwrite(str(mask_path), np.array([[255, 0], [0, 255]], dtype=np.uint8))
    monkeypatch.setattr("clayfield.ui.image_panel.QFileDialog.getOpenFileName", lambda *args: (str(secondary_path), ""))
    win.image_panel.composition_controls["import_secondary"].click()
    wait_for(app, lambda: win.state.secondary_field is not None)
    monkeypatch.setattr("clayfield.ui.image_panel.QFileDialog.getOpenFileName", lambda *args: (str(mask_path), ""))
    win.image_panel.composition_controls["import_mask"].click()
    wait_for(app, lambda: win.state.mask_field is not None)
    assert win.state.composition_settings["enabled"]
    assert win.state.mask_source_descriptor["type"] == "heightmap"


def test_procedural_project_can_save_and_reopen_in_window(window, tmp_path: Path):
    win, app = window
    win.image_panel.source_mode.setCurrentText("Wave interference")
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    project = save_project(win.state, tmp_path / "procedural-ui.clayfield")
    restored = ProjectState()
    load_project(project, restored)
    assert restored.source_type == "wave_interference"
    assert restored.source_image is None
    assert restored.pipeline_snapshot is not None


def test_procedural_heightmap_export_regenerates_at_export_resolution(window, tmp_path: Path, monkeypatch):
    win, app = window
    win.image_panel.source_mode.setCurrentText("Mandelbrot")
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    assert win.state.source_type == "mandelbrot"
    win.terrain_panel.export_resolution.setValue(32)
    output = tmp_path / "procedural.png"
    monkeypatch.setattr(
        "clayfield.ui.main_window.QFileDialog.getSaveFileName", lambda *args: (str(output), "PNG 16-bit (*.png)")
    )
    monkeypatch.setattr("clayfield.ui.main_window.ExportPreviewDialog.exec", lambda self: QDialog.DialogCode.Accepted)
    win._export_heightmap()
    wait_for(app, lambda: not win._export_active)
    pixels = cv2.imread(str(output), cv2.IMREAD_UNCHANGED)
    assert pixels.shape == (32, 32)
    assert pixels.dtype == np.uint16


def test_opened_project_restores_controls_without_becoming_dirty(window, tmp_path: Path):
    win, app = window
    pixels = np.array([[[20, 90, 180], [40, 80, 200]]], dtype=np.uint8)
    state = ProjectState(
        source_path=tmp_path / "original.png",
        source_image=pixels,
        inverted=True,
        adjustment_settings={"linear_light": True, "inverted": True},
    )
    project = save_project(state, tmp_path / "saved.clayfield")
    win.image_panel.controls["Brightness"].setValue(0.5)
    load_project(project, win.state)
    win.image_panel.refresh_from_state()
    win.terrain_panel.sync_from_state()
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    assert not win.state.dirty
    assert win.image_panel.controls["Brightness"].value() == 0
    assert win.image_panel.linear_light.isChecked()
    assert win.state.inverted


def test_new_project_resets_controls_and_rejects_stale_results(window, tmp_path: Path):
    win, app = window
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.zeros((2, 4), dtype=np.uint8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    win.terrain_panel.width.setValue(120)
    assert win.terrain_panel.depth.value() == 60
    win.state.dirty = False
    old_generation = win._heightfield_generation
    win._new_project()
    win._heightfield_finished(old_generation, None, np.ones((2, 2), dtype=np.float32))
    assert win.state.physical_heightfield is None
    assert win.state.source_image is None
    assert win.terrain_panel.width.value() == 100
    assert win.terrain_panel.depth.value() == 100


def test_heightmap_export_uses_current_inverted_image(window, tmp_path: Path, monkeypatch):
    win, app = window
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.array([[0, 255], [0, 255]], dtype=np.uint8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    win.image_panel._apply_invert()
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    win.terrain_panel.export_resolution.setValue(32)
    output = tmp_path / "heightmap.tiff"
    monkeypatch.setattr(
        "clayfield.ui.main_window.QFileDialog.getSaveFileName", lambda *args: (str(output), "TIFF files (*.tif *.tiff)")
    )
    monkeypatch.setattr("clayfield.ui.main_window.ExportPreviewDialog.exec", lambda self: QDialog.DialogCode.Accepted)
    win._export_heightmap()
    wait_for(app, lambda: not win._export_active)
    pixels = cv2.imread(str(output), cv2.IMREAD_UNCHANGED)
    assert pixels.dtype == np.uint16
    assert pixels[0, 0] == 65535
    assert pixels[0, -1] == 0


def test_heightmap_export_supports_eight_bits(window, tmp_path: Path, monkeypatch):
    win, app = window
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.array([[0, 255], [0, 255]], dtype=np.uint8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    win.terrain_panel.export_resolution.setValue(32)
    output = tmp_path / "heightmap.png"
    monkeypatch.setattr(
        "clayfield.ui.main_window.QFileDialog.getSaveFileName", lambda *args: (str(output), "PNG 8-bit (*.png)")
    )
    monkeypatch.setattr("clayfield.ui.main_window.ExportPreviewDialog.exec", lambda self: QDialog.DialogCode.Accepted)
    win._export_heightmap()
    wait_for(app, lambda: not win._export_active)
    assert cv2.imread(str(output), cv2.IMREAD_UNCHANGED).dtype == np.uint8


def test_undo_redo_restores_parameter_and_clean_state(window, tmp_path: Path, monkeypatch):
    win, app = window
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.array([[0, 255], [0, 255]], dtype=np.uint8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    project = tmp_path / "project.clayfield"
    monkeypatch.setattr("clayfield.ui.main_window.QFileDialog.getSaveFileName", lambda *args: (str(project), ""))
    win._save_project()
    assert not win.state.dirty
    win.image_panel.controls["Brightness"].setValue(0.1)
    win.image_panel.controls["Brightness"].setValue(0.2)
    assert win.state.dirty and win.undo_action.isEnabled()
    win._undo()
    wait_for(app, lambda: win.state.adjusted_image is not None)
    assert win.image_panel.controls["Brightness"].value() == 0
    assert not win.state.dirty
    win._redo()
    wait_for(app, lambda: win.state.adjusted_image is not None)
    assert win.image_panel.controls["Brightness"].value() == 0.2
    assert win.state.dirty


def test_undo_width_keeps_image_and_aspect_ratio(window, tmp_path: Path):
    win, app = window
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.zeros((2, 4), dtype=np.uint8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    pixels = win.state.source_image
    win.terrain_panel.width.setValue(120)
    win._undo()
    assert win.state.source_image is pixels
    assert win.terrain_panel.width.value() == 100
    assert win.terrain_panel.depth.value() == 50


def test_background_load_does_not_repopulate_a_new_project(window, tmp_path: Path, monkeypatch):
    from clayfield.ui import image_panel

    win, app = window
    path = tmp_path / "slow.png"
    assert cv2.imwrite(str(path), np.zeros((4, 4), dtype=np.uint8))
    started, release = threading.Event(), threading.Event()
    original = image_panel._load_and_convert

    def slow_load(*args):
        started.set()
        assert release.wait(5)
        return original(*args)

    monkeypatch.setattr(image_panel, "_load_and_convert", slow_load)
    win.image_panel.load_path(str(path))
    try:
        assert started.wait(2)
        win.state.dirty = False
        win._new_project()
    finally:
        release.set()
    wait_for(app, lambda: not win.image_panel._load_workers)
    assert win.state.source_image is None


def test_autosave_does_not_publish_stale_snapshot(window, tmp_path: Path, monkeypatch):
    import clayfield.ui.main_window as main_window

    win, app = window
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.zeros((4, 4), dtype=np.uint8))
    monkeypatch.setattr("clayfield.app.recovery.recovery_directory", lambda: tmp_path)
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    started, release = threading.Event(), threading.Event()
    original = main_window.prepare_recovery_snapshot

    def slow_save(state):
        started.set()
        assert release.wait(5)
        return original(state)

    monkeypatch.setattr(main_window, "prepare_recovery_snapshot", slow_save)
    win._autosave()
    try:
        assert started.wait(2)
        win.terrain_panel.width.setValue(120)
    finally:
        release.set()
    wait_for(app, lambda: win._autosave_worker is None)
    assert not (tmp_path / "untitled.clayfield").exists()
    assert not list(tmp_path.glob(".pending-*.clayfield"))


def test_crop_updates_preview_aspect_without_changing_source(window, tmp_path: Path):
    win, app = window
    source = np.arange(32, dtype=np.uint8).reshape(4, 8)
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), source)
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    assert win.terrain_panel.depth.value() == 50
    win.image_panel.crop_controls[2].setValue(50)
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    assert win.state.adjusted_image.shape == (4, 4)
    assert win.terrain_panel.depth.value() == 100
    np.testing.assert_array_equal(win.state.source_image, source)
    win.image_panel.preview_mode.setCurrentText("Final heightmap")
    assert win.image_panel.preview.pixmap() is not None


def test_slider_exact_input_reset_and_dark_theme(window):
    win, app = window
    spin = win.image_panel.controls["Brightness"]
    row = spin.parentWidget()
    slider = row.findChild(QSlider)
    reset = row.findChild(QToolButton)
    slider.setValue(25)
    assert spin.value() == 0.25
    spin.setValue(-0.35)
    assert slider.value() == -35
    reset.click()
    assert spin.value() == 0
    win._set_dark_theme(True)
    assert app.palette().color(QPalette.ColorRole.Window).name() == "#25292e"
    assert win._settings.value("dark_theme", type=bool)
    win._set_dark_theme(False)


def test_base_and_export_resolution_do_not_recompute_heightfield(window, tmp_path: Path):
    win, app = window
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.zeros((4, 4), dtype=np.uint8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    original = win.state.physical_heightfield
    generation = win._heightfield_generation
    win.terrain_panel.base_thickness.setValue(7)
    win.terrain_panel.export_resolution.setValue(64)
    assert win.state.physical_heightfield is original
    assert win._heightfield_generation == generation


def test_preview_reports_mesh_validation_and_minimum_wall(window, tmp_path: Path):
    from clayfield.ui.export_preview import ExportPreviewDialog

    win, app = window
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.zeros((4, 4), dtype=np.uint8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    dialog = ExportPreviewDialog(win.state, "STL", win)
    wait_for(app, lambda: dialog._worker is None)
    assert "watertight" in dialog.validation.text()
    assert "minimum wall" in dialog.summary.text()
    win.terrain_panel.relief_mode.setCurrentText("Negative")
    assert "insufficient base" in win.terrain_panel.height_info.text()


def test_terrain_reset_and_undo(window, tmp_path: Path):
    win, app = window
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.zeros((4, 4), dtype=np.uint8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    win.terrain_panel.height_offset.setValue(2)
    assert win.state.height_offset_mm == 2
    win.terrain_panel.reset()
    assert win.state.height_offset_mm == 0
    win._undo()
    assert win.state.height_offset_mm == 2


def test_edited_heightmap_export_matches_authoritative_preview(window, tmp_path: Path, monkeypatch):
    win, app = window
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.arange(64, dtype=np.uint8).reshape(8, 8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    win.image_panel.crop_controls[2].setValue(25)
    win.terrain_panel.height_invert.setChecked(True)
    win.terrain_panel.height_scale.setValue(1.5)
    win.terrain_panel.height_offset.setValue(2.0)
    win.terrain_panel.export_resolution.setValue(32)
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    image = win.state.physical_heightfield
    output = tmp_path / "edited.png"
    monkeypatch.setattr(
        "clayfield.ui.main_window.QFileDialog.getSaveFileName", lambda *args: (str(output), "PNG 16-bit (*.png)")
    )
    monkeypatch.setattr("clayfield.ui.main_window.ExportPreviewDialog.exec", lambda self: QDialog.DialogCode.Accepted)
    win._export_heightmap()
    wait_for(app, lambda: not win._export_active)
    pixels = cv2.imread(str(output), cv2.IMREAD_UNCHANGED)
    expected = np.rint((image - image.min()) / (image.max() - image.min()) * 65535).astype(np.uint16)
    np.testing.assert_array_equal(pixels, expected)


def test_preset_ui_load_is_undoable(window, tmp_path: Path, monkeypatch):
    win, app = window
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), np.zeros((4, 4), dtype=np.uint8))
    win.image_panel.load_path(str(path))
    wait_for(app, lambda: win.state.physical_heightfield is not None)
    win.terrain_panel.height_offset.setValue(3)
    preset = tmp_path / "preset.json"
    monkeypatch.setattr("clayfield.ui.main_window.QFileDialog.getSaveFileName", lambda *args: (str(preset), ""))
    monkeypatch.setattr("clayfield.ui.main_window.QFileDialog.getOpenFileName", lambda *args: (str(preset), ""))
    win._save_preset()
    win.terrain_panel.height_offset.setValue(1)
    win._load_preset()
    assert win.state.height_offset_mm == 3
    win._undo()
    assert win.state.height_offset_mm == 1


def test_external_field_wrappers_are_cached_until_field_changes(window):
    win, app = window
    win.state.secondary_field = np.zeros((4, 4), dtype=np.float32)
    win.state.secondary_source_descriptor = {
        "type": "image",
        "schema_version": 1,
        "parameters": {},
        "algorithm": None,
        "algorithm_version": None,
        "seed": None,
        "content_hash": "secondary-hash",
    }
    first = win._external_fields()
    second = win._external_fields()
    assert first is second
    assert first["secondary-hash"] is second["secondary-hash"]
    win.state.secondary_field = np.ones((4, 4), dtype=np.float32)
    third = win._external_fields()
    assert third is not first
    assert third["secondary-hash"] is not first["secondary-hash"]


def test_histogram_samples_large_image(window):
    win, app = window
    image = np.zeros((2000, 2000), dtype=np.float32)
    win.image_panel.histogram.set_image(image, max_samples=1000)
    assert win.image_panel.histogram.values.shape == (256,)
    assert float(win.image_panel.histogram.values.max()) == 1.0


def test_viewport_decimates_large_heightfield_for_display(window):
    win, app = window
    heightfield = np.zeros((5000, 5000), dtype=np.float32)
    display, rows, columns = win.viewport._decimate_for_display(heightfield)
    assert max(rows, columns) <= 4096
    assert display.shape == (rows, columns)


def _bump_heightfield(size: int = 41, height: float = 2.0) -> np.ndarray:
    heightfield = np.zeros((size, size), dtype=np.float32)
    centre = size // 2
    heightfield[centre - 2 : centre + 2, centre - 2 : centre + 2] = height
    return heightfield


def _install_sculpt_field(win) -> np.ndarray:
    heightfield = _bump_heightfield()
    win.state.physical_heightfield = heightfield
    win.state.sculpt_base = None
    win.state.sculpt_offsets = None
    win.state.terrain_width_mm = 100.0
    win.state.terrain_depth_mm = 100.0
    return heightfield


def test_sculpt_stroke_updates_the_heightfield_and_keeps_the_layer_identity(window):
    win, app = window
    heightfield = _install_sculpt_field(win)
    original = heightfield.copy()
    win.sculpt_panel.radius.setValue(15.0)
    win.sculpt_panel.strength.setValue(0.8)
    win.sculpt_panel.enable.setCurrentText("On")
    assert win.viewport.sculpt_mode
    win.viewport.sculpt_pressed.emit(0.0, 0.0)
    win.viewport.sculpt_moved.emit(20.0, 0.0)
    win.viewport.sculpt_released.emit()
    assert not np.array_equal(win.state.physical_heightfield, original)
    assert win.state.sculpt_base is not None
    assert win.state.sculpt_offsets is not None
    np.testing.assert_allclose(
        win.state.physical_heightfield, win.state.sculpt_base + win.state.sculpt_offsets, atol=1e-6
    )
    assert np.any(win.state.sculpt_offsets != 0.0)
    assert win.state.dirty
    assert win.undo_action.isEnabled()


def test_sculpt_stroke_undo_and_redo_restore_the_surface(window):
    win, app = window
    heightfield = _install_sculpt_field(win)
    original = heightfield.copy()
    win.sculpt_panel.radius.setValue(15.0)
    win.sculpt_panel.enable.setCurrentText("On")
    win.viewport.sculpt_pressed.emit(0.0, 0.0)
    win.viewport.sculpt_moved.emit(20.0, 0.0)
    win.viewport.sculpt_released.emit()
    sculpted = win.state.physical_heightfield.copy()
    win._undo()
    np.testing.assert_allclose(win.state.physical_heightfield, original, atol=1e-6)
    np.testing.assert_allclose(win.state.sculpt_offsets, 0.0, atol=1e-6)
    assert win.redo_action.isEnabled()
    win._redo()
    np.testing.assert_allclose(win.state.physical_heightfield, sculpted, atol=1e-6)


def test_sculpt_stroke_undo_after_a_parameter_change_walks_both_stacks(window):
    win, app = window
    heightfield = _install_sculpt_field(win)
    original = heightfield.copy()
    win.sculpt_panel.radius.setValue(15.0)
    win.sculpt_panel.enable.setCurrentText("On")
    win.viewport.sculpt_pressed.emit(0.0, 0.0)
    win.viewport.sculpt_moved.emit(20.0, 0.0)
    win.viewport.sculpt_released.emit()
    sculpted = win.state.physical_heightfield.copy()
    # A terrain parameter edit lands on top of the sculpt stroke in the ledger.
    win.terrain_panel.width.setValue(110.0)
    assert win.undo_action.isEnabled()
    win._undo()
    # The parameter change is undone first, so the sculpt stroke stays applied.
    np.testing.assert_allclose(win.state.physical_heightfield, sculpted, atol=1e-6)
    win._undo()
    np.testing.assert_allclose(win.state.physical_heightfield, original, atol=1e-6)
    win._redo()
    np.testing.assert_allclose(win.state.physical_heightfield, sculpted, atol=1e-6)


def test_new_project_discards_the_sculpt_layer(window):
    win, app = window
    _install_sculpt_field(win)
    win.sculpt_panel.enable.setCurrentText("On")
    win.viewport.sculpt_pressed.emit(0.0, 0.0)
    win.viewport.sculpt_released.emit()
    assert win.state.sculpt_offsets is not None
    win.state.dirty = False
    win._new_project()
    assert win.state.sculpt_base is None
    assert win.state.sculpt_offsets is None
    assert not win.sculpt_history.can_undo


def test_viewport_brush_radius_is_validated_and_tracks_the_panel(window):
    win, app = window
    with pytest.raises(ValueError, match="radius"):
        win.viewport.set_brush_radius(0.0)
    win.sculpt_panel.radius.setValue(12.5)
    assert win.viewport.brush_radius_mm == pytest.approx(12.5)


def test_viewport_picks_the_surface_under_the_pointer(window):
    win, app = window
    win.viewport.resize(800, 600)
    heightfield = np.zeros((41, 41), dtype=np.float32)
    win.viewport.set_heightfield(heightfield, 100.0, 100.0)
    hit = win.viewport._pick(400, 300)
    assert hit is not None
    assert hit.x_mm == pytest.approx(0.0, abs=1.0)
    assert hit.z_mm == pytest.approx(0.0, abs=1.0)


def _mouse_event(kind, x, y, button, buttons):
    position = QPointF(float(x), float(y))
    return QMouseEvent(kind, position, position, button, buttons, Qt.KeyboardModifier.NoModifier)


def test_sculpt_mode_right_drag_orbits_the_camera(window):
    """The left button belongs to the brush, so the camera needs another gesture."""
    win, app = window
    win.viewport.resize(800, 600)
    win.viewport.set_heightfield(np.zeros((41, 41), dtype=np.float32), 100.0, 100.0)
    win.sculpt_panel.enable.setCurrentText("On")
    orbits: list[tuple[float, float]] = []
    original = win.viewport.camera.orbit
    win.viewport.camera.orbit = lambda dx, dy: orbits.append((dx, dy))
    try:
        win.viewport.mousePressEvent(
            _mouse_event(QEvent.Type.MouseButtonPress, 120, 120, Qt.MouseButton.RightButton, Qt.MouseButton.RightButton)
        )
        win.viewport.mouseMoveEvent(
            _mouse_event(QEvent.Type.MouseMove, 150, 140, Qt.MouseButton.NoButton, Qt.MouseButton.RightButton)
        )
        win.viewport.mouseReleaseEvent(
            _mouse_event(QEvent.Type.MouseButtonRelease, 150, 140, Qt.MouseButton.RightButton, Qt.MouseButton.NoButton)
        )
    finally:
        win.viewport.camera.orbit = original
    assert orbits, "right-drag must orbit while the brush owns the left button"
    assert not win.viewport._sculpting


def test_sculpt_undo_returns_the_document_to_the_saved_state(window):
    """Undoing the last stroke onto a saved layer must clear the dirty marker."""
    win, app = window
    _install_sculpt_field(win)
    win.sculpt_panel.radius.setValue(15.0)
    win.sculpt_panel.enable.setCurrentText("On")
    win.viewport.sculpt_pressed.emit(0.0, 0.0)
    win.viewport.sculpt_moved.emit(20.0, 0.0)
    win.viewport.sculpt_released.emit()
    assert win.state.dirty
    # Simulate a save: the sculpted layer and the parameter stack become clean.
    win.state.dirty = False
    win.history.record(win.state)
    win.history.mark_clean()
    win._remember_sculpt_clean()
    win._update_title()
    # A second stroke is an unsaved change on top of the saved layer.
    win.viewport.sculpt_pressed.emit(-10.0, 0.0)
    win.viewport.sculpt_moved.emit(10.0, 5.0)
    win.viewport.sculpt_released.emit()
    assert win.state.dirty
    assert win.undo_action.isEnabled()
    win._undo()
    assert not win._sculpt_changed()
    assert not win.state.dirty
    assert "*" not in win.windowTitle()


def test_sculpt_panel_close_hides_the_controls_and_disables_the_brush(window):
    win, app = window
    win.sculpt_panel.enable.setCurrentText("On")
    assert win.viewport.sculpt_mode
    win.sculpt_panel.close_button.click()
    assert win.sculpt_panel.isHidden()
    assert not win.viewport.sculpt_mode
    assert not win.sculpt_action.isChecked()
    # The View menu is the way back, and it restores the panel without silently
    # re-arming the brush.
    win.sculpt_action.setChecked(True)
    assert not win.sculpt_panel.isHidden()
    assert not win.viewport.sculpt_mode
    assert not win.sculpt_panel.enabled


def test_sculpt_panel_set_enabled_does_not_reemit_the_toggle(window):
    win, app = window
    events: list[bool] = []
    win.sculpt_panel.sculpt_toggled.connect(events.append)
    win.sculpt_panel.set_enabled(True)
    assert win.sculpt_panel.enabled
    assert events == []
    win.sculpt_panel.set_enabled(False)
    assert not win.sculpt_panel.enabled
    assert events == []


def test_brush_panel_repositions_when_the_viewport_reports_its_own_resize(window):
    """The parent's resizeEvent runs before layout, so the panel needs its own cue.

    A position computed from the parent's stale viewport size leaves the panel
    floating mid-canvas. The viewport reports its final size instead, and that
    signal must move the bottom-anchored overlay to the corner.
    """
    win, app = window
    win.resize(1200, 800)
    app.processEvents()
    viewport = win.viewport
    panel = win.sculpt_panel
    panel.move(12, 12)  # stand in for a position computed before the layout
    viewport.resized.emit()
    assert panel.x() == 12
    assert panel.y() == max(12, viewport.height() - panel.height() - 12)
    win.resize(900, 620)
    app.processEvents()
    for _ in range(3):
        app.processEvents()
    assert panel.y() == max(12, viewport.height() - panel.height() - 12)
