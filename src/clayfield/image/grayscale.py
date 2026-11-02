"""Luminance-aware grayscale conversion."""

from __future__ import annotations

import cv2
import numpy as np


def to_grayscale(image: np.ndarray, *, linear_light: bool = False) -> np.ndarray:
    """Convert pixels to luminance; BGRA alpha is preserved in source but ignored."""
    if image.ndim == 2:
        result = image.astype(np.float32)
        maximum = 255.0 if image.dtype == np.uint8 else 65535.0
        return np.clip(result / maximum, 0.0, 1.0).astype(np.float32)
    if image.ndim != 3 or image.shape[2] not in (3, 4):
        raise ValueError(f"Expected grayscale, BGR, or BGRA image; got {image.shape}")

    maximum = 255.0 if image.dtype == np.uint8 else 65535.0
    values = np.clip(image[..., :3].astype(np.float32) / maximum, 0.0, 1.0)
    if not linear_light:
        code = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
        return np.clip(code / maximum, 0.0, 1.0).astype(np.float32)

    # Convert sRGB BGR channels to linear light before luminance weighting.
    linear = np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)
    result = linear[..., 0] * 0.0722 + linear[..., 1] * 0.7152 + linear[..., 2] * 0.2126
    return np.clip(result, 0.0, 1.0).astype(np.float32)


def invert(image: np.ndarray) -> np.ndarray:
    """Invert a normalized grayscale image without modifying the input."""
    values = np.asarray(image, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError(f"Expected a 2D grayscale image; got {values.shape}")
    return (1.0 - np.clip(values, 0.0, 1.0)).astype(np.float32)
