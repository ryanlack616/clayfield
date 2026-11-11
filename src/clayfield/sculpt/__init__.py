"""Localized, surface-aware sculpting operations for ClayField.

The sculpting subsystem edits the authoritative CPU heightfield. ClayField does
not keep a triangle mesh in the interactive path: ``generate_solid_mesh`` builds
the closed solid on demand for STL/3MF export. A brush therefore paints a
displacement into the heightfield, and export still sees the sculpted surface.

Coordinate convention (shared with the viewport and the heightfield module):

* ``heightfield[row, column]`` is millimetres above the base plane.
* ``row`` increases with ``+z``; ``column`` increases with ``+x``.
* ``x`` spans ``[-width_mm / 2, +width_mm / 2]`` and ``z`` spans
  ``[-depth_mm / 2, +depth_mm / 2]``.
* The viewport renders in ``mm / 20`` units, so a ray produced in viewport units
  must have its origin scaled by 20 before intersecting a heightfield in mm.
"""

from clayfield.sculpt.brush import ALGORITHMS, BrushSettings
from clayfield.sculpt.brush_query import BrushRegion, compute_region
from clayfield.sculpt.falloff import FALLOFFS, falloff_weight
from clayfield.sculpt.history import SculptEdit, SculptHistory, SculptStroke, apply_stroke
from clayfield.sculpt.session import SculptSession
from clayfield.sculpt.smooth_bilateral import smooth_bilateral
from clayfield.sculpt.smooth_laplacian import laplacian_delta, smooth_laplacian
from clayfield.sculpt.smooth_taubin import smooth_taubin
from clayfield.sculpt.stroke import StrokePoint, interpolate_stroke
from clayfield.sculpt.surface_picking import (
    Ray,
    SurfaceHit,
    height_at_mm,
    intersect_heightfield,
    ray_from_screen,
)

__all__ = [
    "ALGORITHMS",
    "FALLOFFS",
    "BrushRegion",
    "BrushSettings",
    "Ray",
    "SculptEdit",
    "SculptHistory",
    "SculptSession",
    "SculptStroke",
    "StrokePoint",
    "SurfaceHit",
    "apply_stroke",
    "compute_region",
    "falloff_weight",
    "height_at_mm",
    "interpolate_stroke",
    "intersect_heightfield",
    "laplacian_delta",
    "ray_from_screen",
    "smooth_bilateral",
    "smooth_laplacian",
    "smooth_taubin",
]
