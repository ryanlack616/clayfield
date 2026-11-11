"""Brush footprint selection on the heightfield grid.

The brush is radial in the heightfield's ``x``/``z`` plane. The returned region
always includes a one-cell margin so a Laplacian stencil at the footprint edge has
real neighbours; the margin carries zero weight and is never modified.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from clayfield.sculpt.brush import BrushSettings
from clayfield.sculpt.falloff import falloff_weight

# The stencil needs one neighbour on every side of a modified cell.
MARGIN_CELLS = 1


@dataclass(frozen=True)
class BrushRegion:
    """A rectangular slice of the heightfield with per-cell influence weights.

    ``weights`` has the same shape as the addressed block and already includes the
    brush strength, so the smoothing kernels apply it directly. ``row0``/``row1``
    and ``col0``/``col1`` are inclusive grid indices, and ``MARGIN_CELLS`` rows and
    columns at each edge are zero-weight stencil support.
    """

    row0: int
    row1: int
    col0: int
    col1: int
    weights: np.ndarray

    @property
    def block_slice(self) -> tuple[slice, slice]:
        """Inclusive bounds expressed as a NumPy basic slice."""
        return slice(self.row0, self.row1 + 1), slice(self.col0, self.col1 + 1)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.row1 - self.row0 + 1, self.col1 - self.col0 + 1)


def compute_region(
    heightfield: np.ndarray,
    x_mm: float,
    z_mm: float,
    width_mm: float,
    depth_mm: float,
    settings: BrushSettings,
) -> BrushRegion | None:
    """Return the affected grid block for a brush centred at ``(x_mm, z_mm)``.

    Returns ``None`` when the footprint misses the grid or carries no influence.
    """
    settings.validate()
    rows, columns = heightfield.shape
    if rows < 2 or columns < 2:
        return None
    if not (math.isfinite(x_mm) and math.isfinite(z_mm)):
        return None
    if not (math.isfinite(width_mm) and math.isfinite(depth_mm)) or width_mm <= 0.0 or depth_mm <= 0.0:
        return None

    spacing_x = width_mm / (columns - 1)
    spacing_z = depth_mm / (rows - 1)
    radius = settings.radius_mm

    col0 = math.floor((x_mm - radius + width_mm / 2.0) / spacing_x) - MARGIN_CELLS
    col1 = math.ceil((x_mm + radius + width_mm / 2.0) / spacing_x) + MARGIN_CELLS
    row0 = math.floor((z_mm - radius + depth_mm / 2.0) / spacing_z) - MARGIN_CELLS
    row1 = math.ceil((z_mm + radius + depth_mm / 2.0) / spacing_z) + MARGIN_CELLS
    col0 = max(0, min(columns - 1, col0))
    col1 = max(0, min(columns - 1, col1))
    row0 = max(0, min(rows - 1, row0))
    row1 = max(0, min(rows - 1, row1))
    if col1 < col0 or row1 < row0:
        return None

    xs = -width_mm / 2.0 + np.arange(col0, col1 + 1, dtype=np.float64) * spacing_x
    zs = -depth_mm / 2.0 + np.arange(row0, row1 + 1, dtype=np.float64) * spacing_z
    distances = np.hypot(xs[None, :] - float(x_mm), zs[:, None] - float(z_mm))
    normalized = distances / radius
    weights = falloff_weight(normalized, settings.falloff) * settings.strength
    if not np.any(weights > 0.0):
        return None
    return BrushRegion(int(row0), int(row1), int(col0), int(col1), weights.astype(np.float32))
