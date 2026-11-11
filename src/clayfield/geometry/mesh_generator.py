"""Closed rectangular relief mesh generation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from clayfield.core.cancellation import check_cancelled


@dataclass(frozen=True)
class SolidMesh:
    """Triangle mesh in millimeters."""

    vertices: np.ndarray
    faces: np.ndarray


def generate_solid_mesh(
    heightfield: np.ndarray,
    width_mm: float,
    depth_mm: float,
    base_thickness_mm: float,
    relief_mode: str = "positive",
    *,
    cancel_check=None,
) -> SolidMesh:
    """Generate a closed solid with a sampled top surface and rectangular base."""
    values = np.asarray(heightfield, dtype=np.float32)
    check_cancelled(cancel_check)
    if values.ndim != 2 or min(values.shape) < 2 or not np.isfinite(values).all():
        raise ValueError("Heightfield must be finite 2D data with at least 2x2 samples")
    if (
        not np.isfinite([width_mm, depth_mm, base_thickness_mm]).all()
        or width_mm <= 0
        or depth_mm <= 0
        or base_thickness_mm <= 0
    ):
        raise ValueError("Physical dimensions and base thickness must be positive")
    if relief_mode not in {"positive", "negative"}:
        raise ValueError("Relief mode must be positive or negative")
    if relief_mode == "negative" and float(np.max(values)) >= base_thickness_mm:
        raise ValueError("Negative relief exceeds base thickness; increase the base or reduce relief")

    rows, columns = values.shape
    x = np.linspace(-width_mm / 2, width_mm / 2, columns, dtype=np.float32)
    z = np.linspace(-depth_mm / 2, depth_mm / 2, rows, dtype=np.float32)
    top_y = values if relief_mode == "positive" else -values
    if float(top_y.min()) <= -base_thickness_mm:
        raise ValueError("Relief intersects the bottom of the base")
    # Broadcasting avoids a Python loop per row and preserves the grid ordering.
    top = np.empty((rows, columns, 3), dtype=np.float32)
    bottom = np.empty_like(top)
    top[:, :, 0] = bottom[:, :, 0] = x
    top[:, :, 1] = top_y
    bottom[:, :, 1] = -base_thickness_mm
    top[:, :, 2] = bottom[:, :, 2] = z[:, None]
    check_cancelled(cancel_check)

    vertices = np.concatenate((top.reshape(-1, 3), bottom.reshape(-1, 3)), axis=0)
    bottom_offset = rows * columns
    grid = np.arange(bottom_offset, dtype=np.int64).reshape(rows, columns)
    a = grid[:-1, :-1].ravel()
    b, d = a + 1, a + columns
    c = d + 1
    cells = a.size
    perimeter = np.concatenate((grid[0, :], grid[1:, -1], grid[-1, -2::-1], grid[-2:0:-1, 0]))
    edge_count = perimeter.size
    faces = np.empty((4 * cells + 2 * edge_count, 3), dtype=np.int64)
    for start in range(0, cells, 131072):
        check_cancelled(cancel_check)
        stop = min(cells, start + 131072)
        aa, bb, cc, dd = a[start:stop], b[start:stop], c[start:stop], d[start:stop]
        faces[4 * start : 4 * stop : 4] = np.column_stack((aa, dd, bb))
        faces[4 * start + 1 : 4 * stop : 4] = np.column_stack((bb, dd, cc))
        faces[4 * start + 2 : 4 * stop : 4] = np.column_stack(
            (aa + bottom_offset, bb + bottom_offset, dd + bottom_offset)
        )
        faces[4 * start + 3 : 4 * stop : 4] = np.column_stack(
            (bb + bottom_offset, cc + bottom_offset, dd + bottom_offset)
        )
    following = np.roll(perimeter, -1)
    faces[4 * cells :: 2] = np.column_stack((perimeter, following, perimeter + bottom_offset))
    faces[4 * cells + 1 :: 2] = np.column_stack((following, following + bottom_offset, perimeter + bottom_offset))
    check_cancelled(cancel_check)
    return SolidMesh(vertices, faces)
