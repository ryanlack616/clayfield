"""Basic image filters for normalized grayscale data."""

from __future__ import annotations

import cv2
import numpy as np


def adjust_brightness_contrast(image: np.ndarray, brightness: float = 0.0, contrast: float = 1.0) -> np.ndarray:
    """Apply brightness in normalized units and multiplicative contrast."""
    values = np.asarray(image, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError(f"Expected a 2D image; got {values.shape}")
    if contrast < 0.0:
        raise ValueError("Contrast must not be negative")
    return np.clip((values - 0.5) * contrast + 0.5 + brightness, 0.0, 1.0).astype(np.float32)


def apply_gamma(image: np.ndarray, gamma: float = 1.0) -> np.ndarray:
    """Apply gamma correction to normalized grayscale data."""
    if gamma <= 0.0:
        raise ValueError("Gamma must be positive")
    values = np.asarray(image, dtype=np.float32)
    return np.power(np.clip(values, 0.0, 1.0), 1.0 / gamma).astype(np.float32)


def gaussian_blur(image: np.ndarray, radius: float = 0.0) -> np.ndarray:
    """Apply Gaussian blur while preserving normalized float32 output."""
    values = np.asarray(image, dtype=np.float32)
    if radius < 0.0:
        raise ValueError("Blur radius must not be negative")
    if radius == 0.0:
        return values.copy()
    kernel = max(3, int(round(radius * 6)) | 1)
    return cv2.GaussianBlur(values, (kernel, kernel), radius).astype(np.float32)


def sharpen(image: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Apply simple unsharp masking."""
    values = np.asarray(image, dtype=np.float32)
    if amount < 0.0:
        raise ValueError("Sharpen amount must not be negative")
    blurred = cv2.GaussianBlur(values, (0, 0), 1.0)
    return np.clip(values + amount * (values - blurred), 0.0, 1.0).astype(np.float32)


def threshold(image: np.ndarray, cutoff: float = 0.5) -> np.ndarray:
    """Convert normalized grayscale data to a binary image."""
    if not 0.0 <= cutoff <= 1.0:
        raise ValueError("Threshold cutoff must be between 0 and 1")
    return (np.asarray(image, dtype=np.float32) >= cutoff).astype(np.float32)
