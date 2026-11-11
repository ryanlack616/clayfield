"""Ray casting against the heightfield surface."""

import numpy as np
import pytest
from PySide6.QtGui import QMatrix4x4

from clayfield.sculpt.surface_picking import Ray, height_at_mm, intersect_heightfield, ray_from_screen
from clayfield.ui.camera import OrbitCamera

VIEWPORT_WIDTH = 800
VIEWPORT_HEIGHT = 600


def _matrices(camera: OrbitCamera, orthographic: bool = False) -> tuple[np.ndarray, np.ndarray]:
    projection = QMatrix4x4()
    aspect = VIEWPORT_WIDTH / VIEWPORT_HEIGHT
    if orthographic:
        half_height = camera.distance * np.tan(np.radians(22.5))
        projection.ortho(-half_height * aspect, half_height * aspect, -half_height, half_height, 0.001, 1000.0)
    else:
        projection.perspective(45.0, aspect, 0.001, 1000.0)
    view = camera.view_matrix()
    projection_array = np.asarray(projection.data(), dtype=np.float64).reshape(4, 4).T
    view_array = np.asarray(view.data(), dtype=np.float64).reshape(4, 4).T
    return projection_array, view_array


def _flat_field(size: int = 41, height: float = 0.0) -> np.ndarray:
    return np.full((size, size), height, dtype=np.float32)


def _top_ray(
    camera: OrbitCamera, orthographic: bool = False, x: float = VIEWPORT_WIDTH / 2, y: float = VIEWPORT_HEIGHT / 2
):
    projection, view = _matrices(camera, orthographic)
    return ray_from_screen(projection, view, x, y, VIEWPORT_WIDTH, VIEWPORT_HEIGHT)


def test_top_view_ray_hits_the_surface_centre():
    camera = OrbitCamera()
    camera.top_view()
    ray = _top_ray(camera)
    # The viewport renders in mm/20, so scale the ray origin into millimetres.
    scaled = Ray(origin=ray.origin * 20.0, direction=ray.direction)
    hit = intersect_heightfield(scaled, _flat_field(), 100.0, 100.0)
    assert hit is not None
    assert abs(hit.x_mm) < 0.5
    assert abs(hit.z_mm) < 0.5
    assert hit.height_mm == pytest.approx(0.0, abs=1e-4)
    assert hit.row == 20
    assert hit.column == 20


def test_ray_hits_a_raised_surface():
    camera = OrbitCamera()
    camera.top_view()
    ray = _top_ray(camera)
    # Scaling the origin into millimetres leaves the direction unit-length, so the
    # ray parameter is measured in millimetres from the camera to the surface.
    scaled = Ray(origin=ray.origin * 20.0, direction=ray.direction)
    heightfield = _flat_field(height=3.0)
    hit = intersect_heightfield(scaled, heightfield, 100.0, 100.0)
    assert hit is not None
    assert hit.height_mm == pytest.approx(3.0, abs=1e-3)
    # The camera sits 120 mm above the base plane after scaling, so a hit on a
    # 3 mm surface is about 117 mm away; the bound only rejects runaway marches.
    assert hit.distance < 200.0


def test_orthographic_top_view_ray_hits_the_surface():
    camera = OrbitCamera()
    camera.top_view()
    ray = _top_ray(camera, orthographic=True)
    scaled = Ray(origin=ray.origin * 20.0, direction=ray.direction)
    hit = intersect_heightfield(scaled, _flat_field(), 100.0, 100.0)
    assert hit is not None
    assert abs(hit.x_mm) < 0.5
    assert abs(hit.z_mm) < 0.5


def test_side_view_ray_hits_the_surface_plane():
    camera = OrbitCamera()
    camera.side_view()
    ray = _top_ray(camera)
    scaled = Ray(origin=ray.origin * 20.0, direction=ray.direction)
    hit = intersect_heightfield(scaled, _flat_field(), 100.0, 100.0)
    assert hit is not None
    assert hit.height_mm == pytest.approx(0.0, abs=1e-3)


def test_ray_misses_when_the_camera_targets_off_the_field():
    # Panning the target outside the terrain moves the centre ray outside the
    # heightfield's x bounds, so there is no surface to hit.
    camera = OrbitCamera()
    camera.top_view()
    camera.target.setX(1000.0)
    ray = _top_ray(camera)
    scaled = Ray(origin=ray.origin * 20.0, direction=ray.direction)
    assert intersect_heightfield(scaled, _flat_field(), 100.0, 100.0) is None


def test_ray_parallel_to_the_surface_above_it_misses():
    ray = Ray(origin=np.array([0.0, 6.0, 0.0]), direction=np.array([1.0, 0.0, 0.0]))
    assert intersect_heightfield(ray, _flat_field(), 100.0, 100.0) is None


def test_ray_from_screen_rejects_degenerate_input():
    projection, view = _matrices(OrbitCamera())
    with pytest.raises(ValueError):
        ray_from_screen(projection, view, 0.0, 0.0, 0, 600)
    with pytest.raises(ValueError):
        ray_from_screen(np.eye(3), view, 0.0, 0.0, 800, 600)


def test_intersect_rejects_non_finite_and_degenerate_fields():
    ray = Ray(origin=np.array([0.0, 6.0, 0.0]), direction=np.array([0.0, -1.0, 0.0]))
    assert intersect_heightfield(ray, np.zeros((1, 1), dtype=np.float32), 100.0, 100.0) is None
    invalid = np.zeros((4, 4), dtype=np.float32)
    invalid[0, 0] = np.nan
    assert intersect_heightfield(ray, invalid, 100.0, 100.0) is None
    assert intersect_heightfield(ray, np.zeros((4, 4), dtype=np.float32), 0.0, 100.0) is None


def test_intersect_rejects_bad_step_budget():
    ray = Ray(origin=np.array([0.0, 6.0, 0.0]), direction=np.array([0.0, -1.0, 0.0]))
    with pytest.raises(ValueError):
        intersect_heightfield(ray, _flat_field(), 100.0, 100.0, max_steps=0)


def test_hit_reports_the_cell_under_the_ray():
    camera = OrbitCamera()
    camera.top_view()
    ray = _top_ray(camera)
    scaled = Ray(origin=ray.origin * 20.0, direction=ray.direction)
    hit = intersect_heightfield(scaled, _flat_field(), 100.0, 100.0)
    assert hit is not None
    # A 41-cell grid over 100 mm places the centre at cell 20.
    assert hit.row == 20
    assert hit.column == 20


def test_height_at_mm_samples_the_grid_and_reports_outside_points():
    heightfield = _flat_field()
    heightfield[20, 20] = 4.0
    # A 41-cell grid over 100 mm puts row/column 20 at the origin.
    assert height_at_mm(0.0, 0.0, heightfield, 100.0, 100.0) == pytest.approx(4.0)
    assert height_at_mm(60.0, 0.0, heightfield, 100.0, 100.0) is None
    assert height_at_mm(0.0, -60.0, heightfield, 100.0, 100.0) is None
