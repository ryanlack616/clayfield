"""Tests for source image loading."""

from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from clayfield.image import loader
from clayfield.image.loader import ImageLoadBudget, ImageLoadError, load_image


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


def _write_png(path: Path, pixels: np.ndarray) -> None:
    assert cv2.imwrite(str(path), pixels)


def test_oversized_image_rejected_before_decode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = np.zeros((4, 4, 3), dtype=np.uint8)
    path = tmp_path / "small.png"
    _write_png(path, source)

    calls = []
    original = loader.ImageOps.exif_transpose

    def _fail_if_called(image):
        calls.append(image)
        raise AssertionError("exif_transpose must not run when the budget rejects the image")

    monkeypatch.setattr(loader.ImageOps, "exif_transpose", _fail_if_called)
    try:
        with pytest.raises(ImageLoadError, match="decoded memory budget"):
            load_image(path, budget=ImageLoadBudget(max_decoded_bytes=1, decode_copies=2))
    finally:
        monkeypatch.setattr(loader.ImageOps, "exif_transpose", original)
    assert calls == []


def test_eight_bit_image_does_not_call_cv2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = np.zeros((4, 4, 3), dtype=np.uint8)
    path = tmp_path / "eight.png"
    _write_png(path, source)

    def _fail(*args, **kwargs):
        raise AssertionError("cv2.imread must not be called for 8-bit images")

    monkeypatch.setattr(cv2, "imread", _fail)
    loaded = load_image(path)
    assert loaded.pixels.dtype == np.uint8
    assert loaded.pixels.shape == source.shape


def test_sixteen_bit_image_uses_cv2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = np.array([[[0, 65535, 1], [1234, 43210, 7]]], dtype=np.uint16)
    path = tmp_path / "sixteen.png"
    _write_png(path, source)

    calls = []
    original = cv2.imread

    def _record(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(cv2, "imread", _record)
    loaded = load_image(path)
    assert len(calls) == 1
    assert loaded.pixels.dtype == np.uint16
    np.testing.assert_array_equal(loaded.pixels, source)


def test_grayscale_8_bit_stays_two_dimensional(tmp_path: Path) -> None:
    source = np.arange(16, dtype=np.uint8).reshape(4, 4)
    path = tmp_path / "gray.png"
    _write_png(path, source)
    loaded = load_image(path)
    assert loaded.pixels.ndim == 2
    assert loaded.channels == 1
    np.testing.assert_array_equal(loaded.pixels, source)


def test_grayscale_alpha_png_is_converted_to_bgra(tmp_path: Path) -> None:
    """LA PNGs have two channels and used to be rejected as unsupported."""
    source = Image.new("LA", (2, 2), (128, 64))
    path = tmp_path / "la.png"
    source.save(path)
    source.close()

    loaded = load_image(path)

    assert loaded.pixels.dtype == np.uint8
    assert loaded.channels == 4
    assert loaded.pixels.shape == (2, 2, 4)
    np.testing.assert_array_equal(loaded.pixels[..., 0], 128)
    np.testing.assert_array_equal(loaded.pixels[..., 1], 128)
    np.testing.assert_array_equal(loaded.pixels[..., 2], 128)
    np.testing.assert_array_equal(loaded.pixels[..., 3], 64)


def test_rgba_8_bit_is_bgra(tmp_path: Path) -> None:
    source = np.array([[[10, 20, 30, 40], [50, 60, 70, 80]]], dtype=np.uint8)
    path = tmp_path / "rgba.png"
    _write_png(path, source)
    loaded = load_image(path)
    assert loaded.pixels.shape == source.shape
    np.testing.assert_array_equal(loaded.pixels, source)


@pytest.mark.parametrize("extension", [".png", ".bmp", ".tif", ".tiff"])
def test_rgb_8_bit_formats_preserve_pixels(tmp_path: Path, extension: str) -> None:
    source = np.array([[[10, 20, 30], [40, 50, 60]]], dtype=np.uint8)
    path = tmp_path / f"source{extension}"
    _write_png(path, source)
    loaded = load_image(path)
    assert loaded.pixels.dtype == np.uint8
    assert loaded.channels == 3
    np.testing.assert_array_equal(loaded.pixels, source)


def test_budget_is_configurable(tmp_path: Path) -> None:
    source = np.zeros((4, 4, 3), dtype=np.uint8)
    path = tmp_path / "budget.png"
    _write_png(path, source)
    small = ImageLoadBudget(max_decoded_bytes=16, decode_copies=2)
    with pytest.raises(ImageLoadError, match="decoded memory budget"):
        load_image(path, budget=small)
    large = ImageLoadBudget(max_decoded_bytes=1024, decode_copies=2)
    loaded = load_image(path, budget=large)
    assert loaded.pixels.shape == source.shape


def test_returned_array_owns_its_data(tmp_path: Path) -> None:
    for dtype, maximum in ((np.uint8, 255), (np.uint16, 65535)):
        source = np.full((4, 4, 3), maximum, dtype=dtype)
        path = tmp_path / f"owned_{dtype.__name__}.png"
        _write_png(path, source)
        loaded = load_image(path)
        assert loaded.pixels.flags.owndata
        assert loaded.pixels.base is None
        assert loaded.pixels.flags.writeable
        np.testing.assert_array_equal(loaded.pixels, source)


def test_rejects_32_bit_precision_before_decode(tmp_path: Path) -> None:
    source = np.zeros((4, 4), dtype=np.int32)
    path = tmp_path / "int32.tif"
    assert cv2.imwrite(str(path), source)
    with pytest.raises(ImageLoadError, match="Unsupported image precision"):
        load_image(path)


def test_rejects_invalid_budget(tmp_path: Path) -> None:
    path = tmp_path / "budget.png"
    _write_png(path, np.zeros((2, 2), dtype=np.uint8))
    with pytest.raises(ImageLoadError, match="budget must be positive"):
        load_image(path, budget=ImageLoadBudget(max_decoded_bytes=0, decode_copies=1))


def test_exif_orientation_survives_16_bit_path(tmp_path: Path) -> None:
    source = np.array([[0, 100], [200, 300]], dtype=np.uint16)
    path = tmp_path / "oriented16.tif"
    image = Image.fromarray(source)
    image.save(path, tiffinfo={274: 6})
    image.close()

    loaded = load_image(path)
    assert loaded.pixels.dtype == np.uint16
    # Orientation 6 is 90 degrees clockwise.
    expected = np.rot90(source, 3)
    np.testing.assert_array_equal(loaded.pixels, expected)
