"""Tests for normalized grayscale processing."""

import numpy as np
import pytest

from clayfield.image.grayscale import invert, to_grayscale


def test_grayscale_is_normalized_float32() -> None:
    source = np.array([[0, 255]], dtype=np.uint8)
    result = to_grayscale(source)
    assert result.dtype == np.float32
    np.testing.assert_allclose(result, [[0.0, 1.0]])


def test_color_grayscale_uses_luminance_conversion() -> None:
    source = np.array([[[255, 0, 0]]], dtype=np.uint8)  # BGR blue
    result = to_grayscale(source)
    assert 0.05 < float(result[0, 0]) < 0.15


def test_invert_does_not_mutate_source() -> None:
    source = np.array([[0.0, 0.25, 1.0]], dtype=np.float32)
    result = invert(source)
    np.testing.assert_allclose(result, [[1.0, 0.75, 0.0]])
    np.testing.assert_allclose(source, [[0.0, 0.25, 1.0]])


def test_invert_requires_2d_input() -> None:
    with pytest.raises(ValueError, match="2D grayscale"):
        invert(np.zeros((2, 2, 1), dtype=np.float32))


def test_bgra_grayscale_ignores_alpha() -> None:
    image = np.array(
        [
            [[10, 20, 30, 0], [10, 20, 30, 255]],
            [[100, 120, 140, 40], [100, 120, 140, 200]],
        ],
        dtype=np.uint8,
    )

    result = to_grayscale(image)

    np.testing.assert_array_equal(result[:, 0], result[:, 1])


def test_linear_light_grayscale_differs_from_srgb_for_midtones() -> None:
    image = np.array([[[64, 64, 64]]], dtype=np.uint8)

    srgb = to_grayscale(image)
    linear = to_grayscale(image, linear_light=True)

    assert linear[0, 0] < srgb[0, 0]
    assert 0.0 < linear[0, 0] < 1.0
