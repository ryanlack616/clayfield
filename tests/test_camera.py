"""Physical camera fitting and view-relative navigation."""

import pytest

from clayfield.ui.camera import OrbitCamera


def test_fit_accounts_for_aspect_and_scene_scale():
    camera = OrbitCamera()
    camera.fit_distance(100, 100, 8, aspect=1)
    square_distance = camera.distance
    assert 5 < square_distance < 20
    camera.fit_distance(100, 100, 8, aspect=0.25)
    assert camera.distance > square_distance
    camera.fit_distance(5000, 5000, 8, aspect=1)
    assert camera.distance > 50


def test_pan_follows_rotated_view_plane():
    camera = OrbitCamera(azimuth=90, elevation=0)
    camera.pan(100, 0, 600)
    assert camera.target.x() == pytest.approx(0, abs=1e-6)
    assert camera.target.z() > 0
