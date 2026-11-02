"""Stable editable tone curves represented as lookup tables."""

from __future__ import annotations

import numpy as np


def curve_lut(points: list[tuple[float, float]], size: int = 4096, interpolation: str = "linear") -> np.ndarray:
    """Build a monotonic piecewise-linear lookup table from control points."""
    if size < 2:
        raise ValueError("Curve LUT size must be at least 2")
    if interpolation not in {"linear", "smoothstep"}:
        raise ValueError("Curve interpolation must be linear or smoothstep")
    if not points:
        points = [(0.0, 0.0), (1.0, 1.0)]
    ordered = sorted((float(x), float(y)) for x, y in points)
    if any(not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0) for x, y in ordered):
        raise ValueError("Curve points must be normalized to 0..1")
    if any(a[0] >= b[0] for a, b in zip(ordered, ordered[1:])):
        raise ValueError("Curve input positions must be strictly increasing")
    if ordered[0][0] > 0.0:
        ordered.insert(0, (0.0, ordered[0][1]))
    if ordered[-1][0] < 1.0:
        ordered.append((1.0, ordered[-1][1]))
    x = np.linspace(0.0, 1.0, size, dtype=np.float32)
    positions = np.array([p[0] for p in ordered], dtype=np.float32)
    outputs = np.array([p[1] for p in ordered], dtype=np.float32)
    indices = np.clip(np.searchsorted(positions, x, side="right") - 1, 0, len(positions) - 2)
    fraction = (x - positions[indices]) / np.maximum(1e-6, positions[indices + 1] - positions[indices])
    if interpolation == "smoothstep":
        fraction = fraction * fraction * (3.0 - 2.0 * fraction)
    return (outputs[indices] + fraction * (outputs[indices + 1] - outputs[indices])).astype(np.float32)


def apply_curve(image: np.ndarray, points: list[tuple[float, float]], interpolation: str = "linear") -> np.ndarray:
    """Apply a normalized tone curve using a generated LUT."""
    values = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
    lut = curve_lut(points, interpolation=interpolation)
    indices = np.rint(values * (len(lut) - 1)).astype(np.intp)
    return lut[indices].astype(np.float32)
