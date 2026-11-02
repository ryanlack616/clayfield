"""Cross-section extraction from the authoritative physical heightfield."""

import numpy as np


def extract_profile(heightfield: np.ndarray, width_mm: float, depth_mm: float, axis: str, index: int):
    values = np.asarray(heightfield, dtype=np.float32)
    if values.ndim != 2 or values.size == 0 or not np.isfinite(values).all():
        raise ValueError("Heightfield must be non-empty finite 2D data")
    rows, columns = values.shape
    if axis == "width":
        if not 0 <= index < rows:
            raise ValueError("Width profile row is out of range")
        profile = values[index, :]
        distance = np.linspace(-width_mm / 2, width_mm / 2, columns, dtype=np.float32)
    elif axis == "depth":
        if not 0 <= index < columns:
            raise ValueError("Depth profile column is out of range")
        profile = values[:, index]
        distance = np.linspace(-depth_mm / 2, depth_mm / 2, rows, dtype=np.float32)
    else:
        raise ValueError("Profile axis must be width or depth")
    return distance, profile.astype(np.float32, copy=False)
