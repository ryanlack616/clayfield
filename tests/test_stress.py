"""Opt-in stress coverage for realistic large source and terrain arrays."""

import os

import numpy as np
import pytest

from clayfield.geometry.estimates import estimate_solid_mesh
from clayfield.geometry.mesh_generator import generate_solid_mesh
from clayfield.image.pipeline import apply_adjustments

pytestmark = pytest.mark.skipif(os.environ.get("CLAYFIELD_STRESS") != "1", reason="Set CLAYFIELD_STRESS=1 for larger workloads")


def test_large_image_adjustment_is_finite_and_deterministic():
    image = np.random.default_rng(42).random((1536, 2048), dtype=np.float32)
    settings = {"Gamma": 1.3, "Blur": 0.8, "Sharpen": 0.4, "Brightness": 0.1}
    points = [(0.0, 0.0), (0.4, 0.25), (1.0, 1.0)]
    first = apply_adjustments(image, settings, points)
    second = apply_adjustments(image, settings, points)
    assert np.isfinite(first).all()
    np.testing.assert_array_equal(first, second)


def test_large_mesh_topology_and_bounds():
    rows, columns = 512, 768
    values = np.linspace(0, 4, rows * columns, dtype=np.float32).reshape(rows, columns)
    mesh = generate_solid_mesh(values, 120, 80, 5)
    estimate = estimate_solid_mesh(rows, columns)
    assert mesh.vertices.shape == (estimate.vertex_count, 3)
    assert mesh.faces.shape == (estimate.triangle_count, 3)
    np.testing.assert_allclose(mesh.vertices.min(axis=0), [-60, -5, -40])
    np.testing.assert_allclose(mesh.vertices.max(axis=0), [60, 4, 40])
    assert mesh.faces.min() == 0 and mesh.faces.max() == len(mesh.vertices) - 1
