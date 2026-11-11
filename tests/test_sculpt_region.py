"""Brush footprint selection on the heightfield grid."""

import numpy as np
import pytest

from clayfield.sculpt.brush import BrushSettings
from clayfield.sculpt.brush_query import compute_region


def _grid(rows=41, columns=41):
    return np.zeros((rows, columns), dtype=np.float32)


def test_region_is_localized_around_the_centre():
    heightfield = _grid()
    region = compute_region(heightfield, 0.0, 0.0, 100.0, 100.0, BrushSettings(radius_mm=10.0))
    assert region is not None
    # A 10 mm radius on a 100 mm grid of 41 columns is 4 cells, plus the stencil
    # margin on each side. The footprint must be far smaller than the full grid.
    assert region.shape[0] < heightfield.shape[0]
    assert region.shape[1] < heightfield.shape[1]
    assert region.row0 >= 0 and region.row1 < heightfield.shape[0]
    assert region.col0 >= 0 and region.col1 < heightfield.shape[1]


def test_region_weights_peak_at_the_centre_and_vanish_at_the_margin():
    heightfield = _grid()
    settings = BrushSettings(radius_mm=10.0, strength=0.5)
    region = compute_region(heightfield, 0.0, 0.0, 100.0, 100.0, settings)
    assert region is not None
    weights = region.weights
    centre_row = (region.row0 + region.row1) // 2
    centre_column = (region.col0 + region.col1) // 2
    peak = weights[centre_row - region.row0, centre_column - region.col0]
    assert peak == pytest.approx(0.5, rel=0.05)
    assert weights.max() <= settings.strength + 1e-6
    # The outermost row and column are stencil support and carry no influence.
    assert np.all(weights[0, :] == 0.0)
    assert np.all(weights[-1, :] == 0.0)
    assert np.all(weights[:, 0] == 0.0)
    assert np.all(weights[:, -1] == 0.0)


def test_region_clips_at_the_grid_edge():
    heightfield = _grid()
    region = compute_region(heightfield, -50.0, -50.0, 100.0, 100.0, BrushSettings(radius_mm=10.0))
    assert region is not None
    assert region.row0 == 0
    assert region.col0 == 0
    assert region.row1 < heightfield.shape[0]


def test_region_returns_none_outside_the_grid():
    heightfield = _grid()
    settings = BrushSettings(radius_mm=2.0)
    assert compute_region(heightfield, 200.0, 0.0, 100.0, 100.0, settings) is None
    assert compute_region(heightfield, 0.0, 200.0, 100.0, 100.0, settings) is None


def test_region_rejects_zero_strength():
    heightfield = _grid()
    assert compute_region(heightfield, 0.0, 0.0, 100.0, 100.0, BrushSettings(strength=0.0)) is None


def test_region_rejects_non_finite_centre():
    heightfield = _grid()
    assert compute_region(heightfield, float("nan"), 0.0, 100.0, 100.0, BrushSettings()) is None


def test_region_rejects_degenerate_grid():
    assert compute_region(np.zeros((1, 1), dtype=np.float32), 0.0, 0.0, 100.0, 100.0, BrushSettings()) is None


def test_region_weights_match_shape():
    heightfield = _grid()
    region = compute_region(heightfield, 3.0, -7.0, 100.0, 100.0, BrushSettings(radius_mm=12.0))
    assert region is not None
    assert region.weights.shape == region.shape
    assert region.weights.dtype == np.float32
