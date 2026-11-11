"""Laplacian, Taubin, and bilateral smoothing kernels."""

import numpy as np
import pytest

from clayfield.sculpt.brush import BrushSettings
from clayfield.sculpt.brush_query import compute_region
from clayfield.sculpt.smooth_bilateral import smooth_bilateral
from clayfield.sculpt.smooth_laplacian import laplacian_delta, smooth_laplacian
from clayfield.sculpt.smooth_taubin import smooth_taubin


def _region(heightfield, settings):
    region = compute_region(heightfield, 0.0, 0.0, 100.0, 100.0, settings)
    assert region is not None
    return region


def _bump_grid(size=41):
    heightfield = np.zeros((size, size), dtype=np.float32)
    centre = size // 2
    heightfield[centre, centre] = 2.0
    return heightfield


def test_laplacian_delta_is_zero_on_a_flat_surface():
    flat = np.zeros((11, 11), dtype=np.float32)
    np.testing.assert_allclose(laplacian_delta(flat), 0.0, atol=1e-7)


def test_flat_surface_stays_flat_after_smoothing():
    flat = np.zeros((41, 41), dtype=np.float32)
    settings = BrushSettings(radius_mm=15.0, strength=0.8)
    region = _region(flat, settings)
    block = flat[region.block_slice]
    smoothed = smooth_laplacian(block, region.weights)
    np.testing.assert_allclose(smoothed, block, atol=1e-7)


def test_laplacian_reduces_a_local_bump():
    heightfield = _bump_grid()
    settings = BrushSettings(radius_mm=15.0, strength=0.6)
    region = _region(heightfield, settings)
    block = heightfield[region.block_slice]
    smoothed = smooth_laplacian(block, region.weights)
    centre = heightfield.shape[0] // 2
    row, column = centre - region.row0, centre - region.col0
    assert smoothed[row, column] < block[row, column]
    assert np.isfinite(smoothed).all()


def test_laplacian_does_not_touch_the_stencil_margin():
    heightfield = _bump_grid()
    settings = BrushSettings(radius_mm=15.0, strength=0.6)
    region = _region(heightfield, settings)
    block = heightfield[region.block_slice]
    smoothed = smooth_laplacian(block, region.weights)
    # The margin ring carries zero weight, so it must be bit-identical.
    np.testing.assert_array_equal(smoothed[0, :], block[0, :])
    np.testing.assert_array_equal(smoothed[-1, :], block[-1, :])
    np.testing.assert_array_equal(smoothed[:, 0], block[:, 0])
    np.testing.assert_array_equal(smoothed[:, -1], block[:, -1])


def test_laplacian_does_not_amplify_high_frequency_detail():
    """The raw Laplacian has an eigenvalue of 8, so a step above 1/4 runs away.

    Smoothing a full-strength stroke over noisy terrain used to multiply the
    highest-frequency component by ``1 - 8*lambda`` on every dab, growing the
    surface by orders of magnitude until the model left the viewport.
    """
    rng = np.random.default_rng(0)
    block = rng.random((64, 64)).astype(np.float32)
    weights = np.ones_like(block)
    peak = float(np.abs(block).max())
    smoothed = block.copy()
    for _ in range(10):
        smoothed = smooth_laplacian(smoothed, weights)
    assert np.isfinite(smoothed).all()
    assert float(np.abs(smoothed).max()) <= peak


def test_taubin_does_not_amplify_high_frequency_detail():
    rng = np.random.default_rng(0)
    block = rng.random((64, 64)).astype(np.float32)
    weights = np.ones_like(block)
    peak = float(np.abs(block).max())
    smoothed = block.copy()
    for _ in range(10):
        smoothed = smooth_taubin(smoothed, weights)
    assert np.isfinite(smoothed).all()
    assert float(np.abs(smoothed).max()) <= peak


def test_laplacian_rejects_an_invalid_lambda():
    block = np.zeros((5, 5), dtype=np.float32)
    weights = np.ones((5, 5), dtype=np.float32)
    with pytest.raises(ValueError, match="lambda"):
        smooth_laplacian(block, weights, lambda_=0.0)
    with pytest.raises(ValueError, match="lambda"):
        smooth_laplacian(block, weights, lambda_=float("nan"))


def test_taubin_rejects_an_unpassive_pair():
    """``1/lambda + 1/mu <= 0`` amplifies a band instead of damping it."""
    block = np.zeros((5, 5), dtype=np.float32)
    weights = np.ones((5, 5), dtype=np.float32)
    with pytest.raises(ValueError, match="passivity"):
        smooth_taubin(block, weights, lambda_=0.5, mu=-0.4)


def test_laplacian_input_is_not_modified():
    heightfield = _bump_grid()
    settings = BrushSettings(radius_mm=15.0, strength=0.6)
    region = _region(heightfield, settings)
    block = heightfield[region.block_slice].copy()
    original = block.copy()
    smooth_laplacian(block, region.weights)
    np.testing.assert_array_equal(block, original)


def test_zero_strength_leaves_the_surface_untouched():
    heightfield = _bump_grid()
    settings = BrushSettings(radius_mm=15.0, strength=0.0)
    region = compute_region(heightfield, 0.0, 0.0, 100.0, 100.0, settings)
    assert region is None


def test_taubin_preserves_more_volume_than_repeated_laplacian():
    heightfield = _bump_grid(size=61)
    settings = BrushSettings(radius_mm=20.0, strength=0.7)
    region = _region(heightfield, settings)
    block = heightfield[region.block_slice]
    laplacian_twice = smooth_laplacian(smooth_laplacian(block, region.weights), region.weights)
    taubin_twice = smooth_taubin(smooth_taubin(block, region.weights), region.weights)
    original_volume = float(block.sum())
    laplacian_volume = float(laplacian_twice.sum())
    taubin_volume = float(taubin_twice.sum())
    assert abs(taubin_volume - original_volume) < abs(laplacian_volume - original_volume)


def test_taubin_rejects_invalid_parameters():
    block = np.zeros((5, 5), dtype=np.float32)
    weights = np.ones((5, 5), dtype=np.float32)
    with pytest.raises(ValueError, match="lambda"):
        smooth_taubin(block, weights, lambda_=0.0)
    with pytest.raises(ValueError, match="mu"):
        smooth_taubin(block, weights, mu=0.1)


def test_taubin_reduces_a_local_bump():
    heightfield = _bump_grid()
    settings = BrushSettings(radius_mm=15.0, strength=0.6, algorithm="taubin")
    region = _region(heightfield, settings)
    block = heightfield[region.block_slice]
    smoothed = smooth_taubin(block, region.weights)
    centre = heightfield.shape[0] // 2
    row, column = centre - region.row0, centre - region.col0
    assert smoothed[row, column] < block[row, column]
    assert np.isfinite(smoothed).all()


def _step_grid(size=41):
    heightfield = np.zeros((size, size), dtype=np.float32)
    heightfield[:, size // 2 :] = 2.0
    return heightfield


def test_bilateral_preserves_a_step_better_than_laplacian():
    heightfield = _step_grid()
    settings = BrushSettings(radius_mm=20.0, strength=0.9)
    region = _region(heightfield, settings)
    block = heightfield[region.block_slice]
    laplacian = smooth_laplacian(block, region.weights)
    bilateral = smooth_bilateral(block, region.weights, sigma_spatial=1.0, sigma_range_mm=0.25)
    centre = heightfield.shape[0] // 2
    row = centre - region.row0
    step_column = heightfield.shape[1] // 2 - region.col0
    # Measure the crest contrast across the step.
    laplacian_contrast = float(laplacian[row, step_column] - laplacian[row, step_column - 1])
    bilateral_contrast = float(bilateral[row, step_column] - bilateral[row, step_column - 1])
    assert bilateral_contrast > laplacian_contrast
    assert np.isfinite(bilateral).all()


def test_bilateral_flat_surface_stays_flat():
    flat = np.zeros((41, 41), dtype=np.float32)
    settings = BrushSettings(radius_mm=15.0, strength=0.8)
    region = _region(flat, settings)
    block = flat[region.block_slice]
    smoothed = smooth_bilateral(block, region.weights)
    np.testing.assert_allclose(smoothed, block, atol=1e-6)


def test_smoothing_weights_shape_mismatch_is_rejected():
    block = np.zeros((5, 5), dtype=np.float32)
    with pytest.raises(ValueError):
        smooth_laplacian(block, np.ones((4, 4), dtype=np.float32))
    with pytest.raises(ValueError):
        smooth_taubin(block, np.ones((4, 4), dtype=np.float32))
    with pytest.raises(ValueError):
        smooth_bilateral(block, np.ones((4, 4), dtype=np.float32))


def test_bilateral_rejects_invalid_sigmas():
    block = np.zeros((5, 5), dtype=np.float32)
    weights = np.ones((5, 5), dtype=np.float32)
    with pytest.raises(ValueError, match="spatial"):
        smooth_bilateral(block, weights, sigma_spatial=0.0)
    with pytest.raises(ValueError, match="range"):
        smooth_bilateral(block, weights, sigma_range_mm=0.0)
