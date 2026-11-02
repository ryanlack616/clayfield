import numpy as np
import pytest

from clayfield.terrain.cross_section import extract_profile


def test_extract_width_and_depth_profiles_in_physical_coordinates():
    field = np.arange(12, dtype=np.float32).reshape(3, 4)
    distance, values = extract_profile(field, 40, 30, "width", 1)
    np.testing.assert_allclose(distance, [-20, -20 / 3, 20 / 3, 20])
    np.testing.assert_array_equal(values, [4, 5, 6, 7])
    distance, values = extract_profile(field, 40, 30, "depth", 2)
    np.testing.assert_allclose(distance, [-15, 0, 15])
    np.testing.assert_array_equal(values, [2, 6, 10])


def test_extract_profile_rejects_invalid_axis_and_index():
    field = np.zeros((2, 2), dtype=np.float32)
    with pytest.raises(ValueError, match="axis"):
        extract_profile(field, 1, 1, "height", 0)
    with pytest.raises(ValueError, match="range"):
        extract_profile(field, 1, 1, "width", 4)
