"""Validated image loading for supported ClayField source formats.

Ownership contract for :func:`load_image` and :func:`load_image_bytes`:

* The returned ``LoadedImage.pixels`` array owns its data. It is never a view
  backed by the Pillow image, which is closed when the loader returns.
* The array is C-contiguous and writable, in ClayField's BGR/BGRA channel order
  for colour images. Grayscale images stay 2D. Grayscale-with-alpha (LA) is
  converted to RGBA so the alpha channel is preserved.
* Callers may mutate the returned array freely; no other owner retains it.

Decoded-memory budget: ``ImageLoadBudget.max_decoded_bytes`` is the estimated
peak for one load, computed as ``width * height * channels * bytes_per_sample *
decode_copies``. It is a memory budget, not a fabrication-resolution cap, and is
configurable per call. The default 6 GiB is the outer bound for large 16-bit
sources. Pillow's own ``DecompressionBombError`` applies at ``Image.open`` time
and rejects sources above ``2 * Image.MAX_IMAGE_PIXELS`` (about 179 megapixels)
regardless of this budget, so the effective ceiling is the smaller of the two.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


class ImageLoadError(RuntimeError):
    """Raised when a source image cannot be loaded or validated."""


@dataclass(frozen=True)
class ImageLoadBudget:
    """Decoded-memory budget for a single image load.

    ``decode_copies`` is the expected number of full-image buffers alive at the
    peak: one for the decode result and one for the channel-order copy. Callers
    with unusual pipelines can raise it.
    """

    max_decoded_bytes: int = 6 * 1024 * 1024 * 1024
    decode_copies: int = 2


DEFAULT_IMAGE_LOAD_BUDGET = ImageLoadBudget()


@dataclass(frozen=True)
class LoadedImage:
    """Original source image and basic metadata."""

    path: Path
    pixels: np.ndarray
    width: int
    height: int
    channels: int
    bit_depth: int


def _png_bit_depth(header: bytes | bytearray | memoryview) -> int | None:
    """Read the PNG IHDR bit depth from a 26-byte header without decoding.

    ``header[12:16]`` is checked against ``b"IHDR"`` so a malformed or
    misidentified stream cannot supply a bogus bit depth from arbitrary bytes.
    """
    if len(header) < 26 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    if header[12:16] != b"IHDR":
        return None
    return int(header[24])


def _png_bit_depth_from_path(path: Path) -> int | None:
    try:
        with path.open("rb") as handle:
            header = handle.read(26)
    except OSError:
        return None
    return _png_bit_depth(header)


def _header_bit_depth(
    source: Image.Image,
    path: Path | None,
    data: bytes | bytearray | memoryview | None = None,
) -> int:
    """Best-effort bit depth from the Pillow header before decoding."""
    if source.format == "PNG":
        if data is not None:
            depth = _png_bit_depth(data[:26])
        elif path is not None:
            depth = _png_bit_depth_from_path(path)
        else:
            depth = None
        if depth is not None:
            return depth
    # Pillow's 16-bit TIFF/BMP modes are explicit; 16-bit RGB BMPs are reduced
    # to 8-bit by Pillow, so the 16-bit signal is the mode, not the format.
    if source.mode in {"I;16", "I;16B", "I;16L", "I;16N"}:
        return 16
    tag_v2 = getattr(source, "tag_v2", None)
    if tag_v2 is not None:
        try:
            bits = tag_v2.get(258)
        except (KeyError, OSError, ValueError):
            bits = None
        if bits is not None:
            values = bits if isinstance(bits, (tuple, list)) else (bits,)
            try:
                return max(int(value) for value in values)
            except (TypeError, ValueError):
                return 8
    return 8


def _estimate_decoded_bytes(width: int, height: int, channels: int, bit_depth: int, copies: int) -> int:
    """Estimate peak decoded memory; Python integers make overflow impossible."""
    bytes_per_sample = max(1, bit_depth // 8)
    return width * height * channels * bytes_per_sample * copies


def _decode_image(
    source: Image.Image,
    *,
    image_path: Path | None,
    data: bytes | bytearray | memoryview | None,
    active: ImageLoadBudget,
    label: str,
) -> LoadedImage:
    """Validate a Pillow header and decode within the active budget."""
    width, height = source.size
    if width <= 0 or height <= 0:
        raise ImageLoadError(f"Image has invalid dimensions: {label}")
    channels = len(source.getbands())
    if channels < 1:
        raise ImageLoadError(f"Image has no channels: {label}")
    bit_depth = _header_bit_depth(source, image_path, data)
    if bit_depth not in (8, 16):
        raise ImageLoadError(f"Unsupported image precision: {bit_depth}-bit")
    estimated = _estimate_decoded_bytes(width, height, channels, bit_depth, active.decode_copies)
    if estimated > active.max_decoded_bytes:
        raise ImageLoadError(
            f"Image exceeds decoded memory budget: estimated {estimated} bytes "
            f"> {active.max_decoded_bytes} bytes ({label})"
        )
    needs_reorder = True
    pixels = None
    if bit_depth <= 8:
        oriented = ImageOps.exif_transpose(source)
        # P/CMYK/YCbCr have no direct RGB channel order; LA is a common PNG
        # variant whose two channels the old code rejected outright. Convert
        # all four to RGB/RGBA so to_grayscale can consume them.
        if oriented.mode in {"P", "CMYK", "YCbCr", "LA"}:
            oriented = oriented.convert("RGBA" if "A" in oriented.getbands() else "RGB")
        # Copy: the Pillow image closes at the end of this block, so the array
        # must own its data rather than view the image buffer.
        pixels = np.asarray(oriented).copy()
    else:
        # 16-bit RGB/RGBA PNG and TIFF: Pillow reduces these to 8 bits, so use
        # OpenCV to keep the source precision. OpenCV applies EXIF orientation
        # itself and returns BGR/BGRA, so no manual transform or channel reorder
        # is required. Archive members arrive as bytes and are decoded in memory.
        if data is not None:
            decoded = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        else:
            decoded = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        if decoded is None or decoded.dtype != np.uint16:
            raise ImageLoadError(f"Could not decode 16-bit image: {label}")
        pixels = decoded
        needs_reorder = False

    if pixels.size == 0:
        raise ImageLoadError(f"Image contains no pixels: {label}")
    # ClayField's UI and OpenCV processing use BGR/BGRA channel order. Pillow
    # returns RGB, so colour images decoded by Pillow need one reorder copy.
    if needs_reorder and pixels.ndim == 3 and pixels.shape[2] == 3:
        pixels = pixels[..., [2, 1, 0]].copy()
    elif needs_reorder and pixels.ndim == 3 and pixels.shape[2] == 4:
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
        path=image_path if image_path is not None else Path(label),
        pixels=pixels,
        width=width,
        height=height,
        channels=channels,
        bit_depth=pixels.dtype.itemsize * 8,
    )


def load_image(path: str | Path, *, budget: ImageLoadBudget | None = None) -> LoadedImage:
    """Load an image without silently discarding its source precision."""
    image_path = Path(path).expanduser()
    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ImageLoadError(f"Unsupported image format: {image_path.suffix or 'none'}")
    if not image_path.is_file():
        raise ImageLoadError(f"Image file does not exist: {image_path}")

    active = budget or DEFAULT_IMAGE_LOAD_BUDGET
    if active.max_decoded_bytes < 1 or active.decode_copies < 1:
        raise ImageLoadError("Image load budget must be positive")

    try:
        with Image.open(image_path) as source:
            return _decode_image(
                source,
                image_path=image_path,
                data=None,
                active=active,
                label=image_path.name,
            )
    except Image.DecompressionBombError as error:
        raise ImageLoadError(f"Image exceeds Pillow's decompression bomb limit: {image_path.name}") from error
    except (OSError, ValueError) as error:
        raise ImageLoadError(f"Could not decode image: {image_path.name}") from error


def load_image_bytes(
    data: bytes | bytearray | memoryview,
    *,
    name: str = "source_image",
    budget: ImageLoadBudget | None = None,
) -> LoadedImage:
    """Decode an in-memory image with the same budget and channel rules.

    Used for archive members so ``.clayfield`` loading cannot bypass the decoded
    memory bound that :func:`load_image` enforces. ``data`` is not copied; the
    Pillow reader and the OpenCV decoder both accept a bytes-like buffer.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise ImageLoadError("Image data must be bytes-like")
    active = budget or DEFAULT_IMAGE_LOAD_BUDGET
    if active.max_decoded_bytes < 1 or active.decode_copies < 1:
        raise ImageLoadError("Image load budget must be positive")

    try:
        with Image.open(io.BytesIO(data)) as source:
            return _decode_image(
                source,
                image_path=None,
                data=data,
                active=active,
                label=name,
            )
    except Image.DecompressionBombError as error:
        raise ImageLoadError(f"Image exceeds Pillow's decompression bomb limit: {name}") from error
    except (OSError, ValueError) as error:
        raise ImageLoadError(f"Could not decode image: {name}") from error
