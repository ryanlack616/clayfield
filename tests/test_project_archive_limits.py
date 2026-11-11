"""Regression tests for .clayfield archive safety limits and resolution validation.

All archives here are tiny synthetic fixtures. Limits are exercised by shrinking
the configurable bounds rather than by allocating large buffers, so the tests
stay fast and memory-cheap while covering the same code paths.
"""

from __future__ import annotations

import json
import warnings
import zipfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from clayfield.app import project_io
from clayfield.app.project_io import (
    ArchiveLimits,
    ProjectIOError,
    load_project,
    save_project,
)
from clayfield.app.project_state import ProjectState


def _encoded_png(size: tuple[int, int] = (2, 2)) -> bytes:
    success, encoded = cv2.imencode(".png", np.zeros(size, dtype=np.uint8))
    assert success
    return encoded.tobytes()


def _metadata(**terrain_overrides) -> dict:
    terrain = {
        "width_mm": 100.0,
        "depth_mm": 100.0,
        "minimum_height_mm": 0.0,
        "maximum_height_mm": 8.0,
        "base_thickness_mm": 5.0,
    }
    terrain.update(terrain_overrides)
    return {
        "version": 4,
        "source_name": "source.png",
        "source": {"type": "image", "schema_version": 1, "parameters": {}, "content_hash": None},
        "pipeline": None,
        "image_geometry": {"crop_margins": [0, 0, 0, 0], "resize": None},
        "terrain": terrain,
        "adjustments": {},
        "curve_points": [[0.0, 0.0], [1.0, 1.0]],
        "mapping_curve_points": [[0.0, 0.0], [1.0, 1.0]],
    }


def _write_archive(path: Path, members: list[tuple[str, bytes]], *, compression=zipfile.ZIP_DEFLATED) -> Path:
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for name, data in members:
            archive.writestr(name, data)
    return path


def _valid_project(path: Path, *, terrain_overrides: dict | None = None) -> Path:
    metadata = _metadata(**(terrain_overrides or {}))
    return _write_archive(
        path,
        [
            ("project.json", json.dumps(metadata).encode("utf-8")),
            ("source_image.png", _encoded_png()),
        ],
    )


def _shrink_limits(monkeypatch: pytest.MonkeyPatch, **overrides) -> None:
    base = ArchiveLimits()
    monkeypatch.setattr(project_io, "DEFAULT_ARCHIVE_LIMITS", ArchiveLimits(**{**base.__dict__, **overrides}))


def test_normal_round_trip_still_loads(tmp_path: Path) -> None:
    source = np.array([[[10, 20, 30], [40, 50, 60]]], dtype=np.uint8)
    state = ProjectState(source_path=tmp_path / "source.png", source_image=source)
    state.heightfield_resolution = (1024, 768)
    state.export_resolution = (2048, 1536)
    project = save_project(state, tmp_path / "roundtrip.clayfield")

    restored = ProjectState()
    load_project(project, restored)
    np.testing.assert_array_equal(restored.source_image, source)
    assert restored.heightfield_resolution == (1024, 768)
    assert restored.export_resolution == (2048, 1536)


def test_embedded_source_image_above_axis_ceiling_is_rejected(tmp_path: Path) -> None:
    """A valid PNG wider than the absolute ceiling must not reach the app."""
    success, encoded = cv2.imencode(".png", np.zeros((1, 20000), dtype=np.uint8))
    assert success
    project = _write_archive(
        tmp_path / "wide.clayfield",
        [
            ("project.json", json.dumps(_metadata()).encode("utf-8")),
            ("source_image.png", encoded.tobytes()),
        ],
    )
    with pytest.raises(ProjectIOError, match="absolute allocation limit"):
        load_project(project, ProjectState())


def test_legitimate_large_source_image_still_loads(tmp_path: Path) -> None:
    """A 2048-square source is well inside the budget and must still load."""
    source = np.zeros((2048, 2048), dtype=np.uint8)
    state = ProjectState(source_path=tmp_path / "source.png", source_image=source)
    project = save_project(state, tmp_path / "large.clayfield")

    restored = ProjectState()
    load_project(project, restored)
    assert restored.source_image is not None
    assert restored.source_image.shape == (2048, 2048)


def test_rejects_oversized_archive_on_disk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _valid_project(tmp_path / "big.clayfield")
    _shrink_limits(monkeypatch, max_compressed_bytes=64)
    with pytest.raises(ProjectIOError, match="archive is too large"):
        load_project(project, ProjectState())


def test_rejects_oversized_member(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b"\0" * 4096
    project = _write_archive(
        tmp_path / "member.clayfield",
        [
            ("project.json", json.dumps(_metadata()).encode("utf-8")),
            ("secondary_original.bin", payload),
            ("source_image.png", _encoded_png()),
        ],
        compression=zipfile.ZIP_STORED,
    )
    _shrink_limits(monkeypatch, max_member_bytes=1024)
    with pytest.raises(ProjectIOError, match="member is too large"):
        load_project(project, ProjectState())


def test_rejects_excessive_total_uncompressed_size(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _write_archive(
        tmp_path / "total.clayfield",
        [
            ("project.json", json.dumps(_metadata()).encode("utf-8")),
            ("secondary_original.bin", b"\0" * 4096),
            ("mask_original.bin", b"\0" * 4096),
            ("source_image.png", _encoded_png()),
        ],
        compression=zipfile.ZIP_STORED,
    )
    _shrink_limits(monkeypatch, max_total_uncompressed_bytes=4096, max_member_bytes=4096)
    with pytest.raises(ProjectIOError, match="expands beyond the limit"):
        load_project(project, ProjectState())


def test_rejects_excessive_compression_ratio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1 MiB of zeros compresses to a few hundred bytes: ratio well over 1:1.
    project = _write_archive(
        tmp_path / "bomb.clayfield",
        [
            ("project.json", json.dumps(_metadata()).encode("utf-8")),
            ("secondary_original.bin", b"\0" * (1024 * 1024)),
            ("source_image.png", _encoded_png()),
        ],
    )
    _shrink_limits(monkeypatch, max_compression_ratio=10)
    with pytest.raises(ProjectIOError, match="compression ratio"):
        load_project(project, ProjectState())


def test_rejects_too_many_members(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    members = [("project.json", json.dumps(_metadata()).encode("utf-8")), ("source_image.png", _encoded_png())]
    # Distinct, allow-listed names so the member-count check is what trips.
    members.append(("secondary_original.bin", b"\0" * 8))
    for extension in (".jpg", ".jpeg", ".tif", ".bmp"):
        members.append((f"source_image{extension}", b"\0" * 8))
    project = _write_archive(tmp_path / "many.clayfield", members)
    _shrink_limits(monkeypatch, max_members=3)
    with pytest.raises(ProjectIOError, match="too many members"):
        load_project(project, ProjectState())


def test_rejects_oversized_project_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _valid_project(tmp_path / "json.clayfield")
    _shrink_limits(monkeypatch, max_project_json_bytes=16)
    with pytest.raises(ProjectIOError, match="member is too large: project.json"):
        load_project(project, ProjectState())


def test_rejects_duplicate_member_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _shrink_limits(monkeypatch)
    path = tmp_path / "dupe.clayfield"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("project.json", json.dumps(_metadata()).encode("utf-8"))
            archive.writestr("source_image.png", _encoded_png())
            archive.writestr("source_image.png", _encoded_png())
    with pytest.raises(ProjectIOError, match="duplicate members"):
        load_project(path, ProjectState())


def test_rejects_unexpected_member(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _shrink_limits(monkeypatch)
    project = _write_archive(
        tmp_path / "extra.clayfield",
        [
            ("project.json", json.dumps(_metadata()).encode("utf-8")),
            ("source_image.png", _encoded_png()),
            ("evil.txt", b"surprise"),
        ],
    )
    with pytest.raises(ProjectIOError, match="unexpected member"):
        load_project(project, ProjectState())


def test_rejects_path_traversal_member(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _shrink_limits(monkeypatch)
    path = tmp_path / "traversal.clayfield"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("project.json", json.dumps(_metadata()).encode("utf-8"))
        archive.writestr("source_image.png", _encoded_png())
        # ZipInfo allows names that the allow-list must reject.
        archive.writestr("../escape.png", _encoded_png())
    with pytest.raises(ProjectIOError, match="unsafe member name|unexpected member"):
        load_project(path, ProjectState())


def test_rejects_missing_project_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _shrink_limits(monkeypatch)
    project = _write_archive(tmp_path / "nometa.clayfield", [("source_image.png", _encoded_png())])
    with pytest.raises(ProjectIOError, match="does not contain project.json"):
        load_project(project, ProjectState())


def test_rejects_malformed_resolution_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _shrink_limits(monkeypatch)
    for bad in ([0, 100], [-1, 100], [2], "big", [2.5, 100], [True, 100]):
        project = _valid_project(tmp_path / "bad-res.clayfield", terrain_overrides={"resolution": bad})
        with pytest.raises(ProjectIOError, match="invalid heightfield resolution"):
            load_project(project, ProjectState())


def test_rejects_non_finite_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _shrink_limits(monkeypatch)
    project = _write_archive(
        tmp_path / "nan.clayfield",
        [
            ("project.json", json.dumps(_metadata(resolution=[float("nan"), 100]), allow_nan=True).encode("utf-8")),
            ("source_image.png", _encoded_png()),
        ],
    )
    with pytest.raises(ProjectIOError, match="invalid heightfield resolution"):
        load_project(project, ProjectState())


def test_rejects_implausible_resolution_above_default_ceiling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _shrink_limits(monkeypatch)
    project = _valid_project(tmp_path / "huge.clayfield", terrain_overrides={"resolution": [20000, 20000]})
    with pytest.raises(ProjectIOError, match="implausible heightfield resolution"):
        load_project(project, ProjectState())


def test_legitimate_large_resolution_metadata_remains_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _shrink_limits(monkeypatch)
    state = ProjectState(source_path=tmp_path / "source.png", source_image=np.zeros((2, 2), dtype=np.uint8))
    # 8192 is large but legitimate for this hardware; it must not be capped at 2048/4096.
    state.heightfield_resolution = (8192, 8192)
    state.export_resolution = (8192, 6144)
    project = save_project(state, tmp_path / "large.clayfield")

    restored = ProjectState()
    load_project(project, restored)
    assert restored.heightfield_resolution == (8192, 8192)
    assert restored.export_resolution == (8192, 6144)


def test_environment_override_cannot_raise_resolution_ceiling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _shrink_limits(monkeypatch)
    # An attacker-controlled environment must not relax the absolute ceiling.
    monkeypatch.setenv("CLAYFIELD_MAX_RESOLUTION_DIMENSION", "20000")
    state = ProjectState(source_path=tmp_path / "source.png", source_image=np.zeros((2, 2), dtype=np.uint8))
    state.heightfield_resolution = (20000, 20000)
    project = save_project(state, tmp_path / "override.clayfield")

    with pytest.raises(ProjectIOError, match="implausible heightfield resolution"):
        load_project(project, ProjectState())


def test_environment_override_cannot_raise_export_resolution_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _shrink_limits(monkeypatch)
    monkeypatch.setenv("CLAYFIELD_MAX_RESOLUTION_DIMENSION", "20000")
    metadata = _metadata()
    metadata["terrain"]["export_resolution"] = [20000, 20000]
    project = _write_archive(
        tmp_path / "override-export.clayfield",
        [
            ("project.json", json.dumps(metadata).encode("utf-8")),
            ("source_image.png", _encoded_png()),
        ],
    )
    with pytest.raises(ProjectIOError, match="implausible export resolution"):
        load_project(project, ProjectState())


def test_environment_override_cannot_lower_ceiling_below_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _shrink_limits(monkeypatch)
    # Even a restrictive override must not change the enforced bound; the
    # function must return the absolute constant regardless of the environment.
    monkeypatch.setenv("CLAYFIELD_MAX_RESOLUTION_DIMENSION", "2")
    assert project_io._max_resolution_dimension() == project_io.MAX_ABSOLUTE_RESOLUTION_DIMENSION


def test_absolute_ceiling_is_a_module_constant() -> None:
    assert project_io._max_resolution_dimension() == 16384
    assert project_io.MAX_ABSOLUTE_RESOLUTION_DIMENSION == 16384


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_schema_versions_1_to_4_still_load(tmp_path: Path, version: int, monkeypatch: pytest.MonkeyPatch) -> None:
    _shrink_limits(monkeypatch)
    metadata = _metadata()
    metadata["version"] = version
    if version < 3:
        metadata.pop("pipeline", None)
        metadata.pop("image_geometry", None)
    if version < 2:
        metadata.pop("adjustments", None)
    project = _write_archive(
        tmp_path / f"v{version}.clayfield",
        [
            ("project.json", json.dumps(metadata).encode("utf-8")),
            ("source_image.png", _encoded_png()),
        ],
    )
    restored = ProjectState()
    load_project(project, restored)
    assert restored.source_image is not None


def test_failed_load_leaves_active_state_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _shrink_limits(monkeypatch, max_compressed_bytes=16)
    project = _valid_project(tmp_path / "reject.clayfield")
    previous = np.ones((3, 3), dtype=np.uint8)
    state = ProjectState(source_image=previous, dirty=True, terrain_width_mm=42)
    with pytest.raises(ProjectIOError):
        load_project(project, state)
    assert state.source_image is previous
    assert state.terrain_width_mm == 42
    assert state.dirty
