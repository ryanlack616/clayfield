"""Tests for 3MF package export."""

from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pytest

from clayfield.export.three_mf import export_3mf
from clayfield.geometry.mesh_generator import generate_solid_mesh


def test_3mf_verification_failure_preserves_existing_destination(tmp_path: Path, monkeypatch) -> None:
    mesh = generate_solid_mesh(np.array([[0.0, 1.0], [1.0, 2.0]], dtype=np.float32), 20.0, 20.0, 3.0)
    destination = tmp_path / "relief.3mf"
    destination.write_bytes(b"known-good")

    def fail_verification(*args, **kwargs):
        raise RuntimeError("verification failed")

    monkeypatch.setattr("clayfield.export.verification.verify_3mf_export", fail_verification)
    with np.testing.assert_raises(RuntimeError):
        export_3mf(mesh, destination)

    assert destination.read_bytes() == b"known-good"
    assert list(tmp_path.glob(".relief.3mf.*.tmp")) == []


def test_3mf_contains_required_package_parts(tmp_path: Path) -> None:
    mesh = generate_solid_mesh(np.array([[0.0, 1.0], [1.0, 2.0]], dtype=np.float32), 20.0, 20.0, 3.0)
    path = export_3mf(mesh, tmp_path / "relief.3mf")
    with ZipFile(path) as archive:
        names = set(archive.namelist())
        assert {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"} <= names
        assert b"millimeter" in archive.read("3D/3dmodel.model")


def test_3mf_reopens_in_independent_lib3mf(tmp_path: Path) -> None:
    lib3mf = pytest.importorskip("lib3mf")
    mesh = generate_solid_mesh(np.array([[0, 1], [2, 3]], dtype=np.float32), 60, 40, 5)
    path = export_3mf(mesh, tmp_path / "relief.3mf")
    model = lib3mf.get_wrapper().CreateModel()
    reader = model.QueryReader("3mf")
    reader.ReadFromFile(str(path))
    assert reader.GetWarningCount() == 0
    assert int(model.GetUnit()) == 1  # millimeters
    meshes = model.GetMeshObjects()
    assert meshes.Count() == 1 and meshes.MoveNext()
    restored = meshes.GetCurrentMeshObject()
    assert restored.GetVertexCount() == len(mesh.vertices)
    assert restored.GetTriangleCount() == len(mesh.faces)
    assert restored.IsManifoldAndOriented()
