"""Ray casting against the heightfield surface.

ClayField renders a heightfield, not a triangle mesh, so picking marches the
camera ray through the heightfield's bounding box and bisects the first sign
change between the ray height and the sampled surface. The matrices accepted by
:func:`ray_from_screen` are 4x4 row-major NumPy arrays, i.e. the transpose of
Qt's column-major ``QMatrix4x4.data()``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# Bisection iterations: 40 halvings of the first bracket reach float precision on
# any realistic terrain, and the loop is bounded so a pathological ray cannot spin.
_BISECTION_STEPS = 40


@dataclass(frozen=True)
class Ray:
    """A world-space ray with a unit-length direction."""

    origin: np.ndarray
    direction: np.ndarray


@dataclass(frozen=True)
class SurfaceHit:
    """The heightfield cell and position under the pointer."""

    row: int
    column: int
    x_mm: float
    z_mm: float
    height_mm: float
    distance: float


def _as_matrix(matrix: np.ndarray) -> np.ndarray:
    array = np.asarray(matrix, dtype=np.float64)
    if array.shape != (4, 4):
        raise ValueError("Projection and view matrices must be 4x4")
    return array


def _transform_point(matrix: np.ndarray, point: np.ndarray) -> np.ndarray:
    homogeneous = matrix @ np.array([point[0], point[1], point[2], 1.0], dtype=np.float64)
    if abs(homogeneous[3]) < 1e-12:
        raise ValueError("Matrix maps the point to infinity")
    return homogeneous[:3] / homogeneous[3]


def ray_from_screen(
    projection: np.ndarray,
    view: np.ndarray,
    x: float,
    y: float,
    width: int,
    height: int,
) -> Ray:
    """Build a world-space ray through pixel ``(x, y)``.

    Pixel coordinates are Qt widget coordinates: ``x`` grows right and ``y`` grows
    down. The result is in the units of the supplied matrices.
    """
    if width <= 0 or height <= 0:
        raise ValueError("Viewport size must be positive")
    projection_matrix = _as_matrix(projection)
    view_matrix = _as_matrix(view)
    inverse_projection = np.linalg.inv(projection_matrix)
    inverse_view = np.linalg.inv(view_matrix)

    ndc_x = 2.0 * float(x) / width - 1.0
    ndc_y = 1.0 - 2.0 * float(y) / height
    near_view = _transform_point(inverse_projection, np.array([ndc_x, ndc_y, -1.0]))
    far_view = _transform_point(inverse_projection, np.array([ndc_x, ndc_y, 1.0]))
    origin = _transform_point(inverse_view, near_view)
    far_world = _transform_point(inverse_view, far_view)
    direction = far_world - origin
    length = float(np.linalg.norm(direction))
    if length < 1e-12:
        raise ValueError("Degenerate camera ray")
    return Ray(origin=origin, direction=direction / length)


def _ray_box(ray: Ray, minimum: np.ndarray, maximum: np.ndarray) -> tuple[float, float] | None:
    """Return the entry and exit distances of a ray through an axis-aligned box."""
    origin = np.asarray(ray.origin, dtype=np.float64)
    direction = np.asarray(ray.direction, dtype=np.float64)
    t_enter = -math.inf
    t_exit = math.inf
    for axis in range(3):
        if abs(direction[axis]) < 1e-12:
            if origin[axis] < minimum[axis] or origin[axis] > maximum[axis]:
                return None
            continue
        first = (minimum[axis] - origin[axis]) / direction[axis]
        second = (maximum[axis] - origin[axis]) / direction[axis]
        if first > second:
            first, second = second, first
        t_enter = max(t_enter, first)
        t_exit = min(t_exit, second)
        if t_enter > t_exit:
            return None
    if t_exit <= 0.0:
        return None
    return max(t_enter, 0.0), t_exit


def _height_at(x_mm: float, z_mm: float, heightfield: np.ndarray, width_mm: float, depth_mm: float) -> float | None:
    """Bilinearly sample the heightfield, or return ``None`` outside the grid."""
    rows, columns = heightfield.shape
    if rows < 2 or columns < 2:
        return None
    column = (x_mm + width_mm / 2.0) * (columns - 1) / width_mm
    row = (z_mm + depth_mm / 2.0) * (rows - 1) / depth_mm
    if row < 0.0 or row > rows - 1 or column < 0.0 or column > columns - 1:
        return None
    col0 = min(int(math.floor(column)), columns - 2)
    row0 = min(int(math.floor(row)), rows - 2)
    frac_col = column - col0
    frac_row = row - row0
    top = heightfield[row0, col0] * (1.0 - frac_col) + heightfield[row0, col0 + 1] * frac_col
    bottom = heightfield[row0 + 1, col0] * (1.0 - frac_col) + heightfield[row0 + 1, col0 + 1] * frac_col
    return float(top * (1.0 - frac_row) + bottom * frac_row)


def height_at_mm(x_mm: float, z_mm: float, heightfield: np.ndarray, width_mm: float, depth_mm: float) -> float | None:
    """Sample the heightfield bilinearly at ``(x_mm, z_mm)``, or return ``None``.

    The sample is ``None`` outside the grid, so callers that need a fallback (the
    brush cursor, for example) can supply one instead of extrapolating a height
    that does not exist.
    """
    return _height_at(x_mm, z_mm, np.asarray(heightfield, dtype=np.float32), width_mm, depth_mm)


def _hit_from_point(
    point: np.ndarray, height_mm: float, width_mm: float, depth_mm: float, rows: int, columns: int, distance: float
) -> SurfaceHit:
    column = min(columns - 1, max(0, int(round((point[0] + width_mm / 2.0) * (columns - 1) / width_mm))))
    row = min(rows - 1, max(0, int(round((point[2] + depth_mm / 2.0) * (rows - 1) / depth_mm))))
    return SurfaceHit(
        row=row,
        column=column,
        x_mm=float(point[0]),
        z_mm=float(point[2]),
        height_mm=height_mm,
        distance=distance,
    )


def intersect_heightfield(
    ray: Ray,
    heightfield: np.ndarray,
    width_mm: float,
    depth_mm: float,
    *,
    max_steps: int = 512,
) -> SurfaceHit | None:
    """Return the first surface crossing along ``ray``, or ``None``.

    ``ray`` and the heightfield must share units; the heightfield's ``x`` spans
    ``[-width_mm / 2, width_mm / 2]`` and its ``z`` spans
    ``[-depth_mm / 2, depth_mm / 2]``.
    """
    if max_steps < 1:
        raise ValueError("max_steps must be at least one")
    values = np.asarray(heightfield, dtype=np.float32)
    if values.ndim != 2 or values.shape[0] < 2 or values.shape[1] < 2:
        return None
    if not (math.isfinite(width_mm) and math.isfinite(depth_mm)) or width_mm <= 0.0 or depth_mm <= 0.0:
        return None
    if not np.isfinite(values).all():
        return None

    minimum = np.array([-width_mm / 2.0, float(values.min()), -depth_mm / 2.0], dtype=np.float64)
    maximum = np.array([width_mm / 2.0, float(values.max()), depth_mm / 2.0], dtype=np.float64)
    bounds = _ray_box(ray, minimum, maximum)
    if bounds is None:
        return None
    t_enter, t_exit = bounds
    step = max((t_exit - t_enter) / max_steps, 1e-6)

    rows, columns = values.shape
    previous: tuple[float, float] | None = None
    t = t_enter
    for _ in range(max_steps + 1):
        point = ray.origin + ray.direction * t
        height = _height_at(point[0], point[2], values, width_mm, depth_mm)
        if height is not None:
            residual = float(point[1] - height)
            if previous is not None and previous[0] * residual <= 0.0:
                low_t, high_t = previous[1], t
                low_residual = previous[0]
                for _ in range(_BISECTION_STEPS):
                    middle_t = 0.5 * (low_t + high_t)
                    middle = ray.origin + ray.direction * middle_t
                    middle_height = _height_at(middle[0], middle[2], values, width_mm, depth_mm)
                    if middle_height is None:
                        break
                    middle_residual = float(middle[1] - middle_height)
                    if low_residual * middle_residual <= 0.0:
                        high_t = middle_t
                    else:
                        low_t = middle_t
                        low_residual = middle_residual
                hit_t = 0.5 * (low_t + high_t)
                hit_point = ray.origin + ray.direction * hit_t
                hit_height = _height_at(hit_point[0], hit_point[2], values, width_mm, depth_mm)
                if hit_height is None:
                    return None
                return _hit_from_point(hit_point, hit_height, width_mm, depth_mm, rows, columns, hit_t)
            previous = (residual, t)
        t += step
    return None
