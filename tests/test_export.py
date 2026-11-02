"""Tests for STL and heightmap export."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from clayfield.export.heightmap import export_heightmap
from clayfield.export.stl import export_stl
from clayfield.geometry.mesh_generator import generate_solid_mesh


def test_heightmap_export_rejects_empty_data(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="non-empty"):
        export_heightmap(np.empty((0, 0), dtype=np.float32), tmp_path / "empty.png")


def test_heightmap_write_failure_preserves_existing_destination(tmp_path: Path, monkeypatch) -> None:
    destination = tmp_path / "heightmap.png"
    destination.write_bytes(b"known-good")
    monkeypatch.setattr("clayfield.export.heightmap.cv2.imwrite", lambda *args: False)

    with pytest.raises(RuntimeError, match="Could not write heightmap"):
        export_heightmap(np.array([[0.0, 1.0], [1.0, 2.0]], dtype=np.float32), destination)

    assert destination.read_bytes() == b"known-good"
    assert list(tmp_path.glob(".heightmap.png.*.png")) == []


def test_stl_export_reopens(tmp_path: Path) -> None:
    mesh = generate_solid_mesh(np.array([[0.0, 1.0], [1.0, 2.0]], dtype=np.float32), 20.0, 20.0, 3.0)
    path = export_stl(mesh, tmp_path / "relief.stl")
    assert path.is_file()
    assert path.stat().st_size > 84


def test_stl_verification_failure_preserves_existing_destination(tmp_path: Path, monkeypatch) -> None:
    mesh = generate_solid_mesh(np.array([[0.0, 1.0], [1.0, 2.0]], dtype=np.float32), 20.0, 20.0, 3.0)
    destination = tmp_path / "relief.stl"
    destination.write_bytes(b"known-good")

    def fail_verification(*args, **kwargs):
        raise RuntimeError("verification failed")

    monkeypatch.setattr("clayfield.export.verification.verify_stl_export", fail_verification)
    with np.testing.assert_raises(RuntimeError):
        export_stl(mesh, destination)

    assert destination.read_bytes() == b"known-good"
    assert list(tmp_path.glob(".relief.stl.*.tmp")) == []


def test_heightmap_export_reopens(tmp_path: Path) -> None:
    path = export_heightmap(np.array([[0.0, 2.0], [1.0, 3.0]], dtype=np.float32), tmp_path / "heightmap.png")
    loaded = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    assert loaded is not None
    assert loaded.dtype == np.uint16
    assert loaded.shape == (2, 2)
