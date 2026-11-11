"""Tests for Milestone 3 image adjustments."""

import numpy as np
import pytest

from clayfield.image.curves import apply_curve, curve_lut
from clayfield.image.filters import adjust_brightness_contrast, apply_gamma, threshold
from clayfield.image.levels import apply_levels
from clayfield.image.pipeline import apply_adjustments


def test_levels_clips_and_applies_gamma() -> None:
    image = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)
    result = apply_levels(image, black_point=0.25, white_point=0.75)
    np.testing.assert_allclose(result, [[0.0, 0.5, 1.0]])


def test_levels_rejects_invalid_range() -> None:
    with pytest.raises(ValueError, match="black point"):
        apply_levels(np.zeros((2, 2), dtype=np.float32), black_point=0.8, white_point=0.2)


def test_curve_identity_is_identity() -> None:
    image = np.array([[0.0, 0.25, 0.75, 1.0]], dtype=np.float32)
    np.testing.assert_allclose(apply_curve(image, [(0.0, 0.0), (1.0, 1.0)]), image, atol=1e-4)


def test_curve_lut_has_requested_size() -> None:
    assert curve_lut([(0.0, 0.0), (0.5, 1.0), (1.0, 1.0)], 128).shape == (128,)


def test_basic_filters_remain_normalized() -> None:
    image = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)
    assert apply_gamma(image, 2.0).min() >= 0.0
    assert adjust_brightness_contrast(image, brightness=0.2).max() <= 1.0
    np.testing.assert_array_equal(threshold(image, 0.5), [[0.0, 1.0, 1.0]])


def test_pipeline_applies_output_levels() -> None:
    image = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)
    result = apply_adjustments(
        image,
        {"Output black": 0.2, "Output white": 0.8},
        [(0.0, 0.0), (1.0, 1.0)],
    )

    np.testing.assert_allclose(result, [[0.2, 0.5, 0.8]], atol=1e-3)


def test_smoothstep_curve_interpolation_is_supported() -> None:
    image = np.array([[0.25, 0.5, 0.75]], dtype=np.float32)
    result = apply_adjustments(
        image,
        {"Curve interpolation": "smoothstep"},
        [(0.0, 0.0), (0.5, 0.2), (1.0, 1.0)],
    )

    assert np.isfinite(result).all()
    assert np.all(np.diff(result[0]) >= 0.0)
