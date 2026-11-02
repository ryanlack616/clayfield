"""Tests for native ClayField project persistence."""



from pathlib import Path
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import pytest

from clayfield.app.project_io import ProjectIOError, autosave_project, load_project, save_project
from clayfield.app.project_state import ProjectState
from clayfield.app.recovery import discard_recovery_snapshot, recovery_path, write_recovery_snapshot
from clayfield.field import PipelineSnapshot, SourceDescriptor
from clayfield.terrain.mapping import MappingSettings


def test_project_round_trip(tmp_path: Path) -> None:
    source = np.array([[[10, 20, 30], [40, 50, 60]]], dtype=np.uint8)
    source_path = tmp_path / "source.png"
    assert cv2.imwrite(str(source_path), source)
    state = ProjectState()
    state.source_path = source_path
    state.source_image = source
    state.terrain_width_mm = 120.0
    state.terrain_depth_mm = 80.0
    state.base_thickness_mm = 6.0
    state.relief_mode = "negative"
    state.smoothing_sigma = 1.5
    state.edge_falloff = 0.25
    state.heightfield_resolution = (256, 256)
    state.inverted = True
    state.adjustment_settings = {"Gamma": 1.4, "threshold_enabled": True, "inverted": True}
    state.curve_points = [(0.0, 0.0), (0.5, 0.7), (1.0, 1.0)]
    state.crop_margins = (10, 20, 5, 0)
    state.image_resize = (320, 240)
    state.height_invert = True
    state.height_normalize = True
    state.height_scale = 1.5
    state.height_offset_mm = 2.0
    state.noise_octaves = 3
    state.edge_falloff_strength = 0.4

    project = save_project(state, tmp_path / "test.clayfield")
    restored = ProjectState()
    load_project(project, restored)

    assert restored.source_image is not None
    np.testing.assert_array_equal(restored.source_image, source)
    assert restored.terrain_width_mm == 120.0
    assert restored.terrain_depth_mm == 80.0
    assert restored.base_thickness_mm == 6.0
    assert restored.relief_mode == "negative"
    assert restored.smoothing_sigma == 1.5
    assert restored.edge_falloff == 0.25
    assert restored.heightfield_resolution == (256, 256)
    assert restored.inverted is True
    assert restored.adjustment_settings == {"Gamma": 1.4, "threshold_enabled": True, "inverted": True}
    assert restored.curve_points == [(0.0, 0.0), (0.5, 0.7), (1.0, 1.0)]
    assert restored.crop_margins == (10, 20, 5, 0)
    assert restored.image_resize == (320, 240)
    assert restored.height_invert and restored.height_normalize
    assert restored.height_scale == 1.5 and restored.height_offset_mm == 2
    assert restored.noise_octaves == 3 and restored.edge_falloff_strength == 0.4


def test_project_embeds_lossless_pixels_for_jpeg_source(tmp_path: Path) -> None:
    source = np.random.default_rng(42).integers(0, 256, (16, 16, 3), dtype=np.uint8)
    state = ProjectState(source_path=tmp_path / "source.jpg", source_image=source)
    project = save_project(state, tmp_path / "lossless.clayfield")
    restored = ProjectState()
    load_project(project, restored)
    np.testing.assert_array_equal(restored.source_image, source)


def test_procedural_project_round_trip_has_no_embedded_image(tmp_path: Path) -> None:
    descriptor = SourceDescriptor(
        source_type="fractal_noise",
        algorithm="value_fbm",
        algorithm_version="1",
        seed=42,
        parameters={"seed": 42, "base_frequency": 2.0, "octaves": 4, "persistence": 0.5, "lacunarity": 2.0, "amplitude": 1.0, "normalization": "auto", "tileable": False},
    )
    pipeline = PipelineSnapshot.from_settings(descriptor, mapping=MappingSettings(maximum_height_mm=5.0))
    state = ProjectState(source_type="fractal_noise", source_descriptor=descriptor.to_dict(), pipeline_snapshot=pipeline.to_dict())
    project = save_project(state, tmp_path / "procedural.clayfield")
    with zipfile.ZipFile(project) as archive:
        metadata = json.loads(archive.read("project.json"))
        assert metadata["version"] == 4
        assert metadata["source"]["type"] == "fractal_noise"
        assert "source_image.png" not in archive.namelist()

    restored = ProjectState()
    load_project(project, restored)
    assert restored.source_image is None
    assert restored.source_path is None
    assert restored.source_type == "fractal_noise"
    assert restored.pipeline_snapshot == pipeline.to_dict()


def test_project_embeds_and_restores_external_secondary_field(tmp_path: Path) -> None:
    secondary = np.array([[0.0, 1.0], [0.5, 0.25]], dtype=np.float32)
    descriptor = SourceDescriptor(source_type="heightmap", content_hash="external-hash", parameters={"filename": "external.png"})
    pipeline = PipelineSnapshot.from_settings(
        SourceDescriptor(
            source_type="fractal_noise",
            algorithm="value_fbm",
            algorithm_version="1",
            seed=2,
            parameters={"seed": 2, "base_frequency": 2.0, "octaves": 2, "persistence": 0.5, "lacunarity": 2.0, "amplitude": 1.0, "normalization": "auto", "tileable": False},
        ),
        mapping=MappingSettings(maximum_height_mm=5.0),
        secondary_source=descriptor,
        composition={"enabled": True, "operation": "blend", "amount": 0.5, "range_policy": "clip"},
    )
    state = ProjectState(source_type="fractal_noise", source_descriptor=pipeline.source.to_dict(), pipeline_snapshot=pipeline.to_dict(), secondary_source_descriptor=descriptor.to_dict(), secondary_field=secondary)
    project = save_project(state, tmp_path / "external.clayfield")
    restored = ProjectState()
    load_project(project, restored)
    np.testing.assert_allclose(restored.secondary_field, secondary, atol=1 / 65535)
    assert restored.secondary_source_descriptor == descriptor.to_dict()


def test_external_field_publication_is_read_only_during_replacement() -> None:
    state = ProjectState(secondary_field=np.zeros((32, 32), dtype=np.float32))
    state.secondary_field.setflags(write=False)
    with pytest.raises(ValueError):
        state.secondary_field[0, 0] = 1.0
    values = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        for index in range(20):
            current = np.full((32, 32), index / 20.0, dtype=np.float32)
            current.setflags(write=False)
            state.secondary_field = current
            values.append(pool.submit(lambda field=current: float(field.mean())))
    assert all(future.result() >= 0.0 for future in values)


def test_autosave_does_not_change_active_project(tmp_path: Path) -> None:
    source = np.full((2, 2), 128, dtype=np.uint8)
    source_path = tmp_path / "source.png"
    assert cv2.imwrite(str(source_path), source)
    state = ProjectState(source_path=source_path, source_image=source, dirty=True)
    active_path = tmp_path / "active.clayfield"
    state.project_path = active_path

    snapshot = autosave_project(state, tmp_path / "snapshot.clayfield")

    assert snapshot.exists()
    assert state.project_path == active_path
    assert state.dirty is True


def test_recovery_snapshot_can_be_created_and_discarded(tmp_path: Path, monkeypatch) -> None:
    source = np.full((2, 2), 128, dtype=np.uint8)
    source_path = tmp_path / "source.png"
    assert cv2.imwrite(str(source_path), source)
    state = ProjectState(source_path=source_path, source_image=source, dirty=True)
    state.project_path = tmp_path / "work.clayfield"
    monkeypatch.setattr("clayfield.app.recovery.recovery_directory", lambda: tmp_path)

    snapshot = write_recovery_snapshot(state)
    assert snapshot == recovery_path(state.project_path)
    assert snapshot.exists()
    discard_recovery_snapshot(state.project_path)
    assert not snapshot.exists()


def test_procedural_recovery_snapshot_can_be_created(tmp_path: Path, monkeypatch) -> None:
    descriptor = SourceDescriptor(
        source_type="fractal_noise",
        algorithm="value_fbm",
        algorithm_version="1",
        seed=4,
        parameters={"seed": 4, "base_frequency": 2.0, "octaves": 2, "persistence": 0.5, "lacunarity": 2.0, "amplitude": 1.0, "normalization": "auto", "tileable": False},
    )
    state = ProjectState(source_type="fractal_noise", source_descriptor=descriptor.to_dict(), dirty=True)
    state.project_path = tmp_path / "procedural.clayfield"
    monkeypatch.setattr("clayfield.app.recovery.recovery_directory", lambda: tmp_path)
    snapshot = write_recovery_snapshot(state)
    assert snapshot.exists()
    discard_recovery_snapshot(state.project_path)
    assert not snapshot.exists()


def test_recovery_paths_distinguish_projects_with_the_same_name(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("clayfield.app.recovery.recovery_directory", lambda: tmp_path)
    assert recovery_path(tmp_path / "first" / "work.clayfield") != recovery_path(tmp_path / "second" / "work.clayfield")


def test_project_rejects_invalid_curve_points(tmp_path: Path) -> None:
    source = np.full((2, 2), 128, dtype=np.uint8)
    source_path = tmp_path / "source.png"
    assert cv2.imwrite(str(source_path), source)
    project = save_project(ProjectState(source_path=source_path, source_image=source), tmp_path / "valid.clayfield")
    rewritten = tmp_path / "invalid-curve.clayfield"
    with zipfile.ZipFile(project) as archive:
        metadata = json.loads(archive.read("project.json"))
        metadata["curve_points"] = [[0.0, 0.0], [0.5, 0.5], [0.5, 1.0]]
        with zipfile.ZipFile(rewritten, "w") as output:
            output.writestr("project.json", json.dumps(metadata))
            output.writestr("source_image.png", archive.read("source_image.png"))
    try:
        load_project(rewritten, ProjectState())
    except ProjectIOError as error:
        assert "curve points" in str(error)
    else:
        raise AssertionError("invalid curve points were accepted")


def test_project_rejects_invalid_resolution(tmp_path: Path) -> None:
    source = np.full((2, 2), 128, dtype=np.uint8)
    source_path = tmp_path / "source.png"
    assert cv2.imwrite(str(source_path), source)
    project = save_project(ProjectState(source_path=source_path, source_image=source), tmp_path / "valid.clayfield")
    rewritten = tmp_path / "invalid-resolution.clayfield"
    with zipfile.ZipFile(project) as archive:
        metadata = json.loads(archive.read("project.json"))
        metadata["terrain"]["export_resolution"] = [1, 2048]
        with zipfile.ZipFile(rewritten, "w") as output:
            output.writestr("project.json", json.dumps(metadata))
            output.writestr("source_image.png", archive.read("source_image.png"))
    try:
        load_project(rewritten, ProjectState())
    except ProjectIOError as error:
        assert "export resolution" in str(error)
    else:
        raise AssertionError("invalid resolution was accepted")


def test_project_round_trip_reproduces_edited_physical_heightfield(tmp_path: Path):
    from clayfield.image.geometry import apply_image_geometry
    from clayfield.image.grayscale import to_grayscale
    from clayfield.image.pipeline import apply_adjustments
    from clayfield.terrain.heightfield import PhysicalDimensions, generate_physical_heightfield, options_from_state

    source = np.arange(100, dtype=np.uint8).reshape(10, 10)
    state = ProjectState(source_path=tmp_path / "source.png", source_image=source, crop_margins=(10, 0, 20, 0), image_resize=(12, 8), height_invert=True, height_normalize=True, height_offset_mm=1.5, height_scale=1.2, noise_octaves=3, noise_amplitude=0.1, noise_seed=7)
    state.adjustment_settings = {"Brightness": 0.2}
    def result(project):
        image = to_grayscale(apply_image_geometry(project.source_image, project.crop_margins, project.image_resize))
        image = apply_adjustments(image, project.adjustment_settings, project.curve_points)
        dims = PhysicalDimensions(project.terrain_width_mm, project.terrain_depth_mm, project.minimum_height_mm, project.maximum_height_mm)
        return generate_physical_heightfield(image, dims, (16, 12), project.height_invert, noise_amplitude=project.noise_amplitude, noise_seed=project.noise_seed, options=options_from_state(project))
    before = result(state)
    path = save_project(state, tmp_path / "edited.clayfield")
    restored = ProjectState()
    load_project(path, restored)
    np.testing.assert_allclose(result(restored), before)
