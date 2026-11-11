"""Stroke sampling and dab spacing."""

import math

import pytest

from clayfield.sculpt.stroke import StrokePoint, interpolate_stroke


def test_stroke_spacing_is_uniform_along_the_segment():
    points = interpolate_stroke((0.0, 0.0), (10.0, 0.0), 2.0)
    assert points[0] == StrokePoint(0.0, 0.0)
    assert points[-1].x_mm == pytest.approx(10.0)
    assert points[-1].z_mm == pytest.approx(0.0)
    gaps = [math.hypot(b.x_mm - a.x_mm, b.z_mm - a.z_mm) for a, b in zip(points, points[1:], strict=False)]
    assert all(gap <= 2.0 + 1e-9 for gap in gaps)


def test_stroke_covers_the_segment_end_point():
    points = interpolate_stroke((0.0, 0.0), (0.0, 7.0), 2.0)
    assert points[-1] == StrokePoint(0.0, 7.0)


def test_include_start_false_skips_the_repeated_junction():
    points = interpolate_stroke((0.0, 0.0), (10.0, 0.0), 2.0, include_start=False)
    assert points[0].x_mm == pytest.approx(2.0)
    assert points[-1].x_mm == pytest.approx(10.0)


def test_zero_length_segment_returns_the_start_only_when_requested():
    assert interpolate_stroke((3.0, 4.0), (3.0, 4.0), 2.0) == [StrokePoint(3.0, 4.0)]
    assert interpolate_stroke((3.0, 4.0), (3.0, 4.0), 2.0, include_start=False) == []


def test_spacing_shorter_than_the_segment_produces_overlapping_dabs():
    points = interpolate_stroke((0.0, 0.0), (1.0, 0.0), 0.25)
    assert len(points) == 5


def test_stroke_rejects_invalid_spacing():
    with pytest.raises(ValueError):
        interpolate_stroke((0.0, 0.0), (1.0, 0.0), 0.0)
    with pytest.raises(ValueError):
        interpolate_stroke((0.0, 0.0), (1.0, 0.0), float("nan"))


def test_stroke_accepts_stroke_point_instances():
    points = interpolate_stroke(StrokePoint(1.0, 2.0), StrokePoint(4.0, 6.0), 5.0)
    assert points[0] == StrokePoint(1.0, 2.0)
    assert points[-1] == StrokePoint(4.0, 6.0)
