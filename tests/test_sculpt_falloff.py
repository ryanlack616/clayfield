"""Falloff curves and brush settings for the sculpting subsystem."""

import numpy as np
import pytest

from clayfield.sculpt.brush import BrushSettings
from clayfield.sculpt.falloff import falloff_weight


def test_falloff_is_one_at_centre_and_zero_at_or_beyond_radius():
    for kind in ("linear", "smoothstep", "gaussian", "constant"):
        assert falloff_weight(0.0, kind) == pytest.approx(1.0)
        for radius in (1.0, 1.5, 4.0):
            assert falloff_weight(radius, kind) == 0.0


def test_smoothstep_matches_the_documented_curve():
    values = falloff_weight(np.array([0.0, 0.25, 0.5, 0.75]), "smoothstep")
    expected = 1.0 - 3.0 * np.array([0.0, 0.25, 0.5, 0.75]) ** 2 + 2.0 * np.array([0.0, 0.25, 0.5, 0.75]) ** 3
    np.testing.assert_allclose(values, expected)


def test_falloff_is_monotonically_non_increasing_inside_the_radius():
    samples = np.linspace(0.0, 1.0, 101)
    for kind in ("linear", "smoothstep", "gaussian"):
        values = falloff_weight(samples, kind)
        assert np.all(np.diff(values) <= 1e-12)


def test_gaussian_is_below_linear_beyond_the_crossing_point():
    # exp(-3 t^2) equals 1 - t at t = 0.5, sits above the ramp below that and
    # below it after. Comparing past the crossing distinguishes the two curves
    # and catches a swapped branch without depending on float ties.
    outer = np.array([0.6, 0.8, 0.9])
    assert np.all(falloff_weight(outer, "gaussian") < falloff_weight(outer, "linear"))


def test_constant_falloff_is_one_until_the_radius():
    np.testing.assert_allclose(falloff_weight(np.array([0.0, 0.5, 0.99]), "constant"), [1.0, 1.0, 1.0])


def test_negative_radius_is_treated_as_the_centre():
    assert falloff_weight(-0.5, "linear") == pytest.approx(1.0)


def test_unknown_falloff_is_rejected():
    with pytest.raises(ValueError, match="Unknown falloff"):
        falloff_weight(0.5, "cubic")


def test_brush_defaults_and_validation():
    settings = BrushSettings()
    settings.validate()
    assert settings.spacing == pytest.approx(0.15 * settings.diameter_mm)
    assert settings.radius_mm * 0.05 == pytest.approx(0.25)


def test_brush_rejects_invalid_settings():
    for settings in (
        BrushSettings(radius_mm=0.0),
        BrushSettings(radius_mm=float("nan")),
        BrushSettings(strength=-0.1),
        BrushSettings(strength=1.1),
        BrushSettings(falloff="cubic"),
        BrushSettings(algorithm="magic"),
        BrushSettings(spacing_mm=0.0),
    ):
        with pytest.raises(ValueError):
            settings.validate()


def test_brush_model_width_relative_radius():
    settings = BrushSettings().with_model_width(200.0)
    assert settings.radius_mm == pytest.approx(10.0)
    assert settings.algorithm == "laplacian"


def test_brush_model_width_rejects_invalid_width():
    with pytest.raises(ValueError):
        BrushSettings().with_model_width(0.0)
