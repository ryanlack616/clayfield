"""Tests for open-top tray framing."""

import numpy as np
import pytest

from clayfield.geometry.container import ContainerSettings, prepare_container_heightfield
from clayfield.geometry.mesh_generator import generate_solid_mesh
from clayfield.geometry.validation import validate_mesh


def test_open_tray_adds_frame_above_the_model_and_validates() -> None:
    field = np.ones((16, 16), dtype=np.float32) * 5.0
    framed, width, depth = prepare_container_heightfield(field, 100, 100, ContainerSettings("open_tray", 2, 2))
    assert framed.shape[0] > field.shape[0] and framed.shape[1] > field.shape[1]
    assert framed.max() == 7.0
    report = validate_mesh(generate_solid_mesh(framed, width, depth, 3.0))
    assert report.valid
    assert report.bounds_mm[1] == (-3.0, 7.0)


def test_open_tray_rejects_negative_relief() -> None:
    with pytest.raises(ValueError, match="positive relief"):
        prepare_container_heightfield(np.zeros((4, 4), dtype=np.float32), 20, 20, ContainerSettings("open_tray"), relief_mode="negative")


def test_open_tray_rejects_walls_larger_than_outside_dimensions() -> None:
    with pytest.raises(ValueError, match="no interior"):
        prepare_container_heightfield(np.zeros((4, 4), dtype=np.float32), 4, 4, ContainerSettings("open_tray", wall_thickness_mm=3))
