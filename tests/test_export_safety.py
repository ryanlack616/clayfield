"""Tests for preflight safeguards around expensive mesh exports."""

from __future__ import annotations

import numpy as np
import pytest

from clayfield.export.tasks import export_mesh_task
from clayfield.terrain.heightfield import PhysicalDimensions


def test_mesh_export_rejects_oversized_resolution_before_processing(tmp_path) -> None:
    image = np.zeros((2, 2), dtype=np.float32)

    with pytest.raises(ValueError, match="reduce export resolution"):
        export_mesh_task(
            image,
            PhysicalDimensions(),
            (4096, 4096),
            5.0,
            "positive",
            tmp_path / "oversized.stl",
            "stl",
        )


def test_mesh_export_rejects_small_resolution(tmp_path) -> None:
    image = np.zeros((2, 2), dtype=np.float32)

    with pytest.raises(ValueError, match="at least 2"):
        export_mesh_task(
            image,
            PhysicalDimensions(),
            (1, 2),
            5.0,
            "positive",
            tmp_path / "invalid.stl",
            "stl",
        )


def test_mesh_export_rejects_fractional_resolution(tmp_path) -> None:
    image = np.zeros((2, 2), dtype=np.float32)

    with pytest.raises(ValueError, match="integer values"):
        export_mesh_task(
            image,
            PhysicalDimensions(),
            (32.5, 32),
            5.0,
            "positive",
            tmp_path / "invalid.stl",
            "stl",
        )


def test_mesh_export_rejects_malformed_resolution(tmp_path) -> None:
    image = np.zeros((2, 2), dtype=np.float32)

    with pytest.raises(ValueError, match="width and height"):
        export_mesh_task(
            image,
            PhysicalDimensions(),
            (512,),
            5.0,
            "positive",
            tmp_path / "invalid.stl",
            "stl",
        )
