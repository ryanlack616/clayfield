"""Levels and tonal adjustment operations."""

from __future__ import annotations

import numpy as np


def apply_levels(
    image: np.ndarray,
    black_point: float = 0.0,
    gamma: float = 1.0,
    white_point: float = 1.0,
    output_black: float = 0.0,
    output_white: float = 1.0,
) -> np.ndarray:
    """Apply validated input/output levels to a normalized grayscale image."""
    values = np.asarray(image, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError(f"Levels requires a 2D image; got {values.shape}")
    if not 0.0 <= black_point < white_point <= 1.0:
        raise ValueError("Levels require 0 <= black point < white point <= 1")
    if gamma <= 0.0:
        raise ValueError("Levels gamma must be positive")
    if not 0.0 <= output_black <= output_white <= 1.0:
        raise ValueError("Output levels must satisfy 0 <= black <= white <= 1")

    normalized = np.clip((values - black_point) / (white_point - black_point), 0.0, 1.0)
    adjusted = normalized ** (1.0 / gamma)
    return (output_black + adjusted * (output_white - output_black)).astype(np.float32)