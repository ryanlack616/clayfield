"""Tests for conservative physical fabrication metrics."""

import numpy as np
import pytest

from benchmarks.fabrication_calibration import generate_calibration_panels
from clayfield.app.cancellation import WorkerCancelled
from clayfield.terrain.fabrication import FabricationProfile, analyze_heightfield


def test_positive_surface_reports_range_and_wall() -> None:
    field = np.array([[0.0, 2.0], [1.0, 5.0]], dtype=np.float32)
    metrics = analyze_heightfield(field, 100.0, 100.0, 3.0)
    assert metrics.minimum_height_mm == 0.0
    assert metrics.maximum_height_mm == 5.0
    assert metrics.relief_range_mm == 5.0
    assert metrics.minimum_wall_mm == 3.0
    assert metrics.exportable


def test_negative_surface_reports_base_thickness_failure() -> None:
    metrics = analyze_heightfield(np.full((4, 4), 4.0, dtype=np.float32), 100, 100, 3, "negative")
    assert metrics.minimum_wall_mm == -1.0
    assert "insufficient_base_thickness" in metrics.warnings
    assert not metrics.exportable


def test_feature_resolution_and_slope_warnings_are_advisory() -> None:
    field = np.array([[0.0, 5.0], [0.0, 5.0]], dtype=np.float32)
    metrics = analyze_heightfield(
        field,
        1.0,
        1.0,
        3.0,
        minimum_feature_width_mm=2.1,
        maximum_slope_degrees=10.0,
    )
    assert "insufficient_sampling_for_feature_width" in metrics.warnings
    assert "surface_slope_exceeds_limit" in metrics.warnings
    assert metrics.exportable


def test_invalid_heightfield_is_blocking() -> None:
    metrics = analyze_heightfield(np.array([[0.0, np.nan], [0.0, 1.0]], dtype=np.float32), 10, 10, 2)
    assert metrics.warnings == ("invalid_heightfield",)
    assert not metrics.exportable


def test_fabrication_thresholds_are_validated() -> None:
    with pytest.raises(ValueError, match="thresholds"):
        analyze_heightfield(np.zeros((2, 2), dtype=np.float32), 10, 10, 2, maximum_slope_degrees=90)


def test_profile_overrides_advisory_limits_for_calibration_fixture() -> None:
    profile = FabricationProfile(
        name="Calibration", minimum_feature_width_mm=20.1, maximum_slope_degrees=10.0, high_frequency_limit=0.01
    )
    metrics = analyze_heightfield(np.array([[0.0, 5.0], [0.0, 5.0]], dtype=np.float32), 10, 10, 3, profile=profile)
    assert "insufficient_sampling_for_feature_width" in metrics.warnings
    assert "surface_slope_exceeds_limit" in metrics.warnings


def test_fabrication_analysis_honors_cancellation() -> None:
    with pytest.raises(WorkerCancelled):
        analyze_heightfield(np.zeros((32, 32), dtype=np.float32), 10, 10, 2, cancel_check=lambda: True)


def test_calibration_panels_generate_both_mesh_formats(tmp_path) -> None:
    paths = generate_calibration_panels(tmp_path, size=24)
    assert len(paths) == 6
    assert {path.suffix for path in paths} == {".stl", ".3mf"}
