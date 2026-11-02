"""Tests for malformed project rejection."""

import json
from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np
import pytest

from clayfield.app.project_io import ProjectIOError, load_project, migrate_project_metadata
from clayfield.app.project_state import ProjectState


def test_rejects_unknown_project_version(tmp_path: Path) -> None:
    image = np.zeros((2, 2), dtype=np.uint8)
    success, encoded = cv2.imencode(".png", image)
    assert success
    path = tmp_path / "bad.clayfield"
    with ZipFile(path, "w") as archive:
        archive.writestr("project.json", json.dumps({"version": 999, "terrain": {}}))
        archive.writestr("source_image.png", encoded.tobytes())
    with pytest.raises(ProjectIOError, match="Unsupported"):
        load_project(path, ProjectState())


def test_invalid_project_does_not_modify_active_state(tmp_path: Path) -> None:
    _, encoded = cv2.imencode(".png", np.zeros((2, 2), dtype=np.uint8))
    path = tmp_path / "bad.clayfield"
    with ZipFile(path, "w") as archive:
        archive.writestr("project.json", json.dumps({"version": 2, "terrain": {"width_mm": -1}}))
        archive.writestr("source_image.png", encoded.tobytes())
    previous = np.ones((3, 3), dtype=np.uint8)
    state = ProjectState(source_image=previous, dirty=True, terrain_width_mm=42)
    with pytest.raises(ProjectIOError):
        load_project(path, state)
    assert state.source_image is previous
    assert state.terrain_width_mm == 42
    assert state.dirty


def test_v1_metadata_is_migrated_without_mutating_the_input():
    old = {"version": 1, "adjustments": {"Gamma": 1.4, "inverted": True}, "terrain": {}}
    migrated = migrate_project_metadata(old)
    assert migrated["version"] == 4
    assert migrated["inverted"] is True
    assert migrated["adjustment_order"] == ["Gamma", "inverted"]
    assert old == {"version": 1, "adjustments": {"Gamma": 1.4, "inverted": True}, "terrain": {}}


def test_v2_metadata_migrates_to_default_image_geometry():
    previous = {"version": 2, "terrain": {"width_mm": 125}, "adjustments": {}}
    current = migrate_project_metadata(previous)
    assert current["version"] == 4
    assert current["terrain"]["width_mm"] == 125
    assert current["image_geometry"] == {"crop_margins": [0, 0, 0, 0], "resize": None}


def test_version_one_project_reopens_and_resaves(tmp_path: Path):
    from clayfield.app.project_io import save_project
    _, encoded = cv2.imencode(".png", np.zeros((2, 2), dtype=np.uint8))
    path = tmp_path / "old.clayfield"
    with ZipFile(path, "w") as archive:
        archive.writestr("project.json", json.dumps({"version": 1, "adjustments": {"inverted": True}, "terrain": {}}))
        archive.writestr("source_image.png", encoded.tobytes())
    state = ProjectState()
    load_project(path, state)
    assert state.inverted
    upgraded = save_project(state, tmp_path / "upgraded.clayfield")
    with ZipFile(upgraded) as archive:
        assert json.loads(archive.read("project.json"))["version"] == 4
