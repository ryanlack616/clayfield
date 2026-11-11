"""Stroke sampling for the sculpting brush.

A stroke is a sequence of dabs spaced along the pointer path. Spacing by arc
length, not by pointer event count, keeps the applied strength independent of how
fast the user moves the mouse.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class StrokePoint:
    """A single dab centre in the heightfield's millimetre coordinates."""

    x_mm: float
    z_mm: float


def interpolate_stroke(
    start: StrokePoint | tuple[float, float],
    end: StrokePoint | tuple[float, float],
    spacing_mm: float,
    *,
    include_start: bool = True,
) -> list[StrokePoint]:
    """Return dab centres from ``start`` to ``end`` inclusive.

    ``include_start`` is false for every segment after the first dab of a stroke:
    the previous segment already placed a dab at its end point, and repeating it
    would double the influence at every vertex of the polyline.
    """
    if not math.isfinite(spacing_mm) or spacing_mm <= 0.0:
        raise ValueError("Stroke spacing must be finite and greater than zero")
    first = start if isinstance(start, StrokePoint) else StrokePoint(float(start[0]), float(start[1]))
    last = end if isinstance(end, StrokePoint) else StrokePoint(float(end[0]), float(end[1]))
    delta_x = last.x_mm - first.x_mm
    delta_z = last.z_mm - first.z_mm
    length = math.hypot(delta_x, delta_z)
    if length <= 1e-9:
        return [first] if include_start else []
    count = max(1, int(math.ceil(length / spacing_mm)))
    first_index = 0 if include_start else 1
    return [
        StrokePoint(first.x_mm + delta_x * index / count, first.z_mm + delta_z * index / count)
        for index in range(first_index, count + 1)
    ]
