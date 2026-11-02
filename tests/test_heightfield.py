"""Tests for physical heightfield generation."""

import numpy as np
import pytest

from clayfield.terrain.heightfield import HeightOptions, PhysicalDimensions, generate_physical_heightfield


def test_heightfield_maps_to_physical_range() -> None:
    image = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)
    result = generate_physical_heightfield(image, PhysicalDimensions(maximum_height_mm=8.0))
    np.testing.assert_allclose(result, [[0.0, 4.0, 8.0]])
    assert result.dtype == np.float32


def test_heightfield_inversion() -> None:
    image = np.array([[0.0, 1.0]], dtype=np.float32)
    result = generate_physical_heightfield(image, PhysicalDimensions(minimum_height_mm=2.0, maximum_height_mm=6.0), inverted=True)
    np.testing.assert_allclose(result, [[6.0, 2.0]])


def test_height_mapping_gamma_is_independent() -> None:
    image = np.array([[0.25, 1.0]], dtype=np.float32)
    result = generate_physical_heightfield(image, PhysicalDimensions(maximum_height_mm=8.0), mapping_gamma=2.0)
    np.testing.assert_allclose(result, [[4.0, 8.0]])


def test_invalid_mapping_gamma_rejected() -> None:
    with pytest.raises(ValueError, match="gamma"):
        generate_physical_heightfield(np.zeros((2, 2), dtype=np.float32), PhysicalDimensions(), mapping_gamma=0.0)


def test_noise_is_reproducible_for_same_seed() -> None:
    image = np.full((32, 32), 0.5, dtype=np.float32)
    first = generate_physical_heightfield(image, PhysicalDimensions(), noise_amplitude=0.2, noise_frequency=2.0, noise_seed=7)
    second = generate_physical_heightfield(image, PhysicalDimensions(), noise_amplitude=0.2, noise_frequency=2.0, noise_seed=7)
    np.testing.assert_array_equal(first, second)


def test_noise_seed_changes_heightfield() -> None:
    image = np.full((32, 32), 0.5, dtype=np.float32)
    first = generate_physical_heightfield(image, PhysicalDimensions(), noise_amplitude=0.2, noise_seed=1)
    second = generate_physical_heightfield(image, PhysicalDimensions(), noise_amplitude=0.2, noise_seed=2)
    assert not np.array_equal(first, second)


def test_negative_noise_seed_is_reproducible() -> None:
    image = np.full((16, 16), 0.5, dtype=np.float32)
    first = generate_physical_heightfield(image, PhysicalDimensions(), noise_amplitude=0.2, noise_seed=-42)
    second = generate_physical_heightfield(image, PhysicalDimensions(), noise_amplitude=0.2, noise_seed=-42)
    np.testing.assert_array_equal(first, second)


def test_mapping_curve_is_applied_independently() -> None:
    image = np.array([[0.25, 1.0]], dtype=np.float32)
    result = generate_physical_heightfield(
        image,
        PhysicalDimensions(maximum_height_mm=8.0),
        mapping_curve_points=[(0.0, 0.0), (0.5, 0.0), (1.0, 1.0)],
    )
    np.testing.assert_allclose(result, [[0.0, 8.0]])


def test_invalid_noise_settings_rejected() -> None:
    image = np.zeros((4, 4), dtype=np.float32)
    with pytest.raises(ValueError, match="amplitude"):
        generate_physical_heightfield(image, PhysicalDimensions(), noise_amplitude=-0.1)
    with pytest.raises(ValueError, match="frequency"):
        generate_physical_heightfield(image, PhysicalDimensions(), noise_frequency=0.0)


def test_heightfield_resolution() -> None:
    image = np.zeros((4, 4), dtype=np.float32)
    result = generate_physical_heightfield(image, PhysicalDimensions(), resolution=(8, 6))
    assert result.shape == (6, 8)


def test_edge_falloff_reduces_border_height() -> None:
    image = np.ones((5, 5), dtype=np.float32)
    result = generate_physical_heightfield(image, PhysicalDimensions(maximum_height_mm=10.0), edge_falloff=0.5)
    assert result[0, 0] == 0.0
    assert result[2, 2] == 10.0


def test_negative_smoothing_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        generate_physical_heightfield(np.zeros((2, 2), dtype=np.float32), PhysicalDimensions(), smoothing_sigma=-1.0)


def test_invalid_dimensions_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        generate_physical_heightfield(np.zeros((2, 2), dtype=np.float32), PhysicalDimensions(width_mm=0))


def test_smoothstep_edge_falloff_is_supported() -> None:
    image = np.ones((9, 9), dtype=np.float32)
    result = generate_physical_heightfield(
        image,
        PhysicalDimensions(maximum_height_mm=10.0),
        edge_falloff=0.5,
        edge_falloff_mode="smoothstep",
    )
    assert result[0, 0] == 0.0
    assert result[4, 4] == 10.0


def test_invalid_edge_falloff_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="falloff mode"):
        generate_physical_heightfield(
            np.ones((3, 3), dtype=np.float32),
            PhysicalDimensions(),
            edge_falloff_mode="cubic",
        )


def test_normalize_clamp_scale_offset_and_height_inversion():
    image = np.array([[0.2, 0.4, 0.6]], dtype=np.float32)
    options = HeightOptions(normalize=True, scale=2, offset_mm=1, clamp_min=0.25, clamp_max=0.75)
    result = generate_physical_heightfield(image, PhysicalDimensions(maximum_height_mm=8), inverted=True, options=options)
    np.testing.assert_allclose(result, [[13, 9, 5]], atol=1e-5)


def test_modifier_strengths_and_fractal_noise_are_reproducible():
    image = np.ones((32, 32), dtype=np.float32) * 0.5
    options = HeightOptions(smoothing_strength=0, edge_strength=0, noise_octaves=4, noise_persistence=0.6)
    first = generate_physical_heightfield(image, PhysicalDimensions(), noise_amplitude=0.2, noise_seed=4, edge_falloff=0.5, options=options)
    second = generate_physical_heightfield(image, PhysicalDimensions(), noise_amplitude=0.2, noise_seed=4, edge_falloff=0.5, options=options)
    np.testing.assert_array_equal(first, second)
    without_noise = generate_physical_heightfield(image, PhysicalDimensions(), edge_falloff=0.5, options=options)
    np.testing.assert_allclose(without_noise, 4)
