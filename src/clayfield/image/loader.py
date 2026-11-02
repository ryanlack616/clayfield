"""Validated image loading for supported ClayField source formats."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


class ImageLoadError(RuntimeError):
    """Raised when a source image cannot be loaded or validated."""


@dataclass(frozen=True)
class LoadedImage:
    """Original source image and basic metadata."""

    path: Path
    pixels: np.ndarray
    width: int
    height: int
    channels: int
    bit_depth: int


def load_image(path: str | Path) -> LoadedImage:
    """Load an image without silently discarding its source precision."""
    image_path = Path(path).expanduser()
    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ImageLoadError(f"Unsupported image format: {image_path.suffix or 'none'}")
    if not image_path.is_file():
        raise ImageLoadError(f"Image file does not exist: {image_path}")

    try:
        with Image.open(image_path) as source:
            orientation = source.getexif().get(274, 1)
            oriented = ImageOps.exif_transpose(source)
            if oriented.mode in {"P", "CMYK", "YCbCr"}:
                oriented = oriented.convert("RGBA" if "A" in oriented.getbands() else "RGB")
            pixels = np.asarray(oriented).copy()
    except (OSError, ValueError) as error:
        raise ImageLoadError(f"Could not decode image: {image_path.name}") from error
    if pixels.size == 0:
        raise ImageLoadError(f"Image contains no pixels: {image_path.name}")
    # Pillow reduces 16-bit RGB/RGBA PNG and TIFF to 8 bits. Decode those
    # with OpenCV and apply the same EXIF transform without losing precision.
    decoded = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if decoded is not None and decoded.dtype == np.uint16:
        transforms = {
            2: lambda a: np.fliplr(a), 3: lambda a: np.rot90(a, 2),
            4: lambda a: np.flipud(a), 5: lambda a: np.swapaxes(a, 0, 1),
            6: lambda a: np.rot90(a, 3),
            7: lambda a: np.flip(np.swapaxes(a, 0, 1), (0, 1)),
            8: lambda a: np.rot90(a, 1),
        }
        pixels = transforms.get(orientation, lambda a: a)(decoded).copy()
    # ClayField's UI and OpenCV processing use BGR/BGRA channel order.
    elif pixels.ndim == 3 and pixels.shape[2] == 3:
        pixels = pixels[..., [2, 1, 0]].copy()
    elif pixels.ndim == 3 and pixels.shape[2] == 4:
        pixels = pixels[..., [2, 1, 0, 3]].copy()
    if pixels.ndim not in (2, 3):
        raise ImageLoadError(f"Unsupported image dimensions: {pixels.shape}")
    if pixels.dtype not in (np.uint8, np.uint16):
        raise ImageLoadError(f"Unsupported image precision: {pixels.dtype}")

    height, width = pixels.shape[:2]
    channels = 1 if pixels.ndim == 2 else pixels.shape[2]
    if channels not in (1, 3, 4):
        raise ImageLoadError(f"Unsupported channel count: {channels}")
    return LoadedImage(
        path=image_path,
        pixels=pixels,
        width=width,
        height=height,
        channels=channels,
        bit_depth=pixels.dtype.itemsize * 8,
    )
