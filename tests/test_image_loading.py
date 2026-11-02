"""Tests for source image loading."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from clayfield.image.loader import ImageLoadError, load_image


def test_load_preserves_16_bit_source(tmp_path: Path) -> None:
    source = np.array([[0, 65535], [1234, 43210]], dtype=np.uint16)
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), source)

    loaded = load_image(path)

    assert loaded.pixels.dtype == np.uint16
    assert loaded.pixels.shape == source.shape
    np.testing.assert_array_equal(loaded.pixels, source)
    assert loaded.bit_depth == 16


def test_load_preserves_rgba_channels_and_16_bit_color(tmp_path: Path) -> None:
    for dtype, maximum in ((np.uint8, 255), (np.uint16, 65535)):
        source = np.array([[[maximum, maximum // 2, 1, maximum // 4]]], dtype=dtype)
        path = tmp_path / f"{dtype.__name__}.png"
        assert cv2.imwrite(str(path), source)
        loaded = load_image(path)
        np.testing.assert_array_equal(loaded.pixels, source)


def test_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ImageLoadError, match="does not exist"):
        load_image(tmp_path / "missing.png")


def test_rejects_unsupported_extension(tmp_path: Path) -> None:
    path = tmp_path / "source.gif"
    path.write_bytes(b"not an image")
    with pytest.raises(ImageLoadError, match="Unsupported image format"):
        load_image(path)


def test_load_applies_exif_orientation(tmp_path: Path) -> None:
    from PIL import Image, ImageOps

    rgb = np.array(
        [
            [[255, 0, 0], [0, 255, 0], [0, 0, 255]],
            [[255, 255, 0], [0, 255, 255], [255, 0, 255]],
        ],
        dtype=np.uint8,
    )
    source = Image.fromarray(rgb, mode="RGB")
    exif = source.getexif()
    exif[274] = 6  # Rotate 90 degrees clockwise.
    path = tmp_path / "oriented.jpg"
    source.save(path, exif=exif, quality=100, subsampling=0)

    loaded = load_image(path)
    expected_rgb = np.asarray(ImageOps.exif_transpose(Image.open(path))).copy()
    expected_bgr = expected_rgb[..., ::-1]

    assert loaded.pixels.shape == expected_bgr.shape
    np.testing.assert_allclose(loaded.pixels, expected_bgr, atol=3)
