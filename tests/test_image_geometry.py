"""Non-destructive source geometry operations."""

import numpy as np
import pytest

from clayfield.image.geometry import apply_image_geometry, processed_dimensions


def test_crop_and_resize_preserve_source():
    source = np.arange(6 * 8, dtype=np.uint16).reshape(6, 8)
    before = source.copy()
    cropped = apply_image_geometry(source, (25, 0, 25, 0))
    np.testing.assert_array_equal(cropped, source[:, 2:6])
    assert processed_dimensions(8, 6, (25, 0, 25, 0), None) == (4, 6)
    resized = apply_image_geometry(source, (25, 0, 25, 0), (12, 10))
    assert resized.shape == (10, 12) and resized.dtype == np.uint16
    np.testing.assert_array_equal(source, before)


def test_rejects_empty_crop_and_invalid_resize():
    with pytest.raises(ValueError, match="non-empty"):
        apply_image_geometry(np.zeros((4, 4), dtype=np.uint8), (50, 0, 50, 0))
    with pytest.raises(ValueError, match="Resize"):
        apply_image_geometry(np.zeros((4, 4), dtype=np.uint8), resize=(1, 10))
