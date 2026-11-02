"""Tests for closed relief mesh generation and validation."""


import numpy as np
import pytest

from clayfield.geometry.mesh_generator import SolidMesh, generate_solid_mesh
from clayfield.geometry.validation import validate_mesh


def test_positive_relief_is_closed_and_dimensioned() -> None:
    heightfield = np.array([[0.0, 2.0], [1.0, 3.0]], dtype=np.float32)
    mesh = generate_solid_mesh(heightfield, 100.0, 80.0, 5.0)
    report = validate_mesh(mesh)
    assert report.valid
    assert report.watertight
    assert report.positive_volume
    assert report.edge_manifold
    assert report.connected_components == 1
    assert report.euler_number == 2
    assert report.non_degenerate
    assert report.bounds_mm == ((-50.0, 50.0), (-5.0, 3.0), (-40.0, 40.0))


def test_negative_relief_has_expected_top_bound() -> None:
    mesh = generate_solid_mesh(np.ones((2, 2), dtype=np.float32), 10.0, 10.0, 2.0, "negative")
    report = validate_mesh(mesh)
    assert report.valid
    assert report.bounds_mm[1] == (-2.0, -1.0)


def test_invalid_relief_mode_rejected() -> None:
    with pytest.raises(ValueError, match="positive or negative"):
        generate_solid_mesh(np.zeros((2, 2), dtype=np.float32), 10.0, 10.0, 2.0, "sideways")


def test_negative_relief_rejects_insufficient_base_thickness() -> None:
    with pytest.raises(ValueError, match="exceeds base thickness"):
        generate_solid_mesh(np.full((2, 2), 3.0, dtype=np.float32), 10.0, 10.0, 3.0, "negative")


def test_validation_rejects_inconsistent_triangle_winding():
    mesh = generate_solid_mesh(np.zeros((3, 3), dtype=np.float32), 10, 10, 2)
    faces = mesh.faces.copy()
    faces[0] = faces[0, ::-1]
    report = validate_mesh(SolidMesh(mesh.vertices, faces))
    assert report.watertight
    assert not report.valid


def test_validation_rejects_disconnected_mesh() -> None:
    first = generate_solid_mesh(np.zeros((2, 2), dtype=np.float32), 10, 10, 2)
    second = generate_solid_mesh(np.zeros((2, 2), dtype=np.float32), 10, 10, 2)
    vertices = np.concatenate((first.vertices, second.vertices + np.array([20, 0, 0], dtype=np.float32)))
    faces = np.concatenate((first.faces, second.faces + len(first.vertices)))
    report = validate_mesh(SolidMesh(vertices, faces))
    assert report.watertight
    assert report.connected_components == 2
    assert not report.valid


def test_validation_reports_open_edge_ownership() -> None:
    mesh = generate_solid_mesh(np.zeros((3, 3), dtype=np.float32), 10, 10, 2)
    report = validate_mesh(SolidMesh(mesh.vertices, mesh.faces[:-1]))
    assert not report.edge_manifold
    assert not report.valid
