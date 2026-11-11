"""Open-top tray framing for positive-relief heightfields."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ContainerSettings:
    """Dimensions for an optional open-top raised perimeter frame."""

    mode: str = "none"
    wall_thickness_mm: float = 2.0
    clearance_above_model_mm: float = 2.0
    outside_dimensions: bool = True

    def validate(self) -> None:
        if self.mode not in {"none", "open_tray"}:
            raise ValueError("Container mode must be none or open_tray")
        if not np.isfinite([self.wall_thickness_mm, self.clearance_above_model_mm]).all():
            raise ValueError("Container dimensions must be finite")
        if self.mode != "none" and (self.wall_thickness_mm <= 0 or self.clearance_above_model_mm < 0):
            raise ValueError("Container wall thickness must be positive and clearance non-negative")


def container_footprint(
    width_mm: float, depth_mm: float, settings: ContainerSettings | None = None
) -> tuple[float, float]:
    """Return the outside footprint represented by container settings."""
    settings = settings or ContainerSettings()
    settings.validate()
    if settings.mode == "none" or settings.outside_dimensions:
        return float(width_mm), float(depth_mm)
    return float(width_mm + 2.0 * settings.wall_thickness_mm), float(depth_mm + 2.0 * settings.wall_thickness_mm)


def prepare_container_heightfield(
    heightfield: np.ndarray,
    width_mm: float,
    depth_mm: float,
    settings: ContainerSettings | None = None,
    *,
    relief_mode: str = "positive",
) -> tuple[np.ndarray, float, float]:
    """Add an open-top raised frame and return field plus resulting footprint.

    The frame is represented on the same regular grid as the relief. Its top is
    above the current maximum surface by the requested clearance. Positive
    relief is required; negative relief needs a separate recessed-tray design.
    """
    settings = settings or ContainerSettings()
    settings.validate()
    values = np.asarray(heightfield, dtype=np.float32)
    if values.ndim != 2 or min(values.shape, default=0) < 2 or not np.isfinite(values).all():
        raise ValueError("Container heightfield must be finite 2D data")
    if width_mm <= 0 or depth_mm <= 0:
        raise ValueError("Container footprint dimensions must be positive")
    if relief_mode not in {"positive", "negative"}:
        raise ValueError("Relief mode must be positive or negative")
    if settings.mode == "none":
        return values.copy(), float(width_mm), float(depth_mm)
    if relief_mode != "positive":
        raise ValueError("Open-top containers currently support positive relief only")

    rows, columns = values.shape
    if settings.outside_dimensions:
        interior_width = width_mm - 2.0 * settings.wall_thickness_mm
        interior_depth = depth_mm - 2.0 * settings.wall_thickness_mm
        if interior_width <= 0 or interior_depth <= 0:
            raise ValueError("Container walls leave no interior relief area")
        outer_width, outer_depth = width_mm, depth_mm
    else:
        interior_width = width_mm
        interior_depth = depth_mm
        outer_width = width_mm + 2.0 * settings.wall_thickness_mm
        outer_depth = depth_mm + 2.0 * settings.wall_thickness_mm

    spacing_x = interior_width / max(1, columns - 1)
    spacing_y = interior_depth / max(1, rows - 1)
    border_x = max(1, int(math.ceil(settings.wall_thickness_mm / max(spacing_x, 1e-6))))
    border_y = max(1, int(math.ceil(settings.wall_thickness_mm / max(spacing_y, 1e-6))))
    inner_columns = columns
    inner_rows = rows
    framed_columns = inner_columns + 2 * border_x
    framed_rows = inner_rows + 2 * border_y
    target_width = outer_width if settings.outside_dimensions else outer_width
    target_depth = outer_depth if settings.outside_dimensions else outer_depth
    inner = values
    wall_top = float(values.max()) + settings.clearance_above_model_mm
    framed = np.full((framed_rows, framed_columns), wall_top, dtype=np.float32)
    framed[border_y : border_y + inner_rows, border_x : border_x + inner_columns] = inner
    return framed, float(target_width), float(target_depth)
