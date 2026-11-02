"""Conservative physical fabrication metrics for height fields."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from clayfield.app.cancellation import check_cancelled


@dataclass(frozen=True)
class FabricationProfile:
    """Generic advisory limits for one fabrication process profile."""

    name: str = "Generic FDM"
    minimum_feature_width_mm: float = 0.4
    maximum_slope_degrees: float = 65.0
    high_frequency_limit: float = 0.15

    def validate(self) -> None:
        if not self.name or not np.isfinite([self.minimum_feature_width_mm, self.maximum_slope_degrees, self.high_frequency_limit]).all():
            raise ValueError("Fabrication profile is invalid")
        if self.minimum_feature_width_mm <= 0 or not 0 < self.maximum_slope_degrees < 90 or self.high_frequency_limit < 0:
            raise ValueError("Fabrication profile limits are invalid")


GENERIC_FDM_PROFILE = FabricationProfile()
FINE_DETAIL_PROFILE = FabricationProfile("Fine Detail", 0.25, 55.0, 0.10)
FABRICATION_PROFILES = {
    GENERIC_FDM_PROFILE.name: GENERIC_FDM_PROFILE,
    FINE_DETAIL_PROFILE.name: FINE_DETAIL_PROFILE,
}


@dataclass(frozen=True)
class FabricationMetrics:
    """Measured or sampled fabrication metrics for one physical surface."""

    minimum_height_mm: float
    maximum_height_mm: float
    relief_range_mm: float
    minimum_wall_mm: float
    sample_spacing_mm: float
    minimum_resolved_feature_width_mm: float
    maximum_slope_degrees: float
    high_frequency_ratio: float
    warnings: tuple[str, ...]

    @property
    def blocking_warnings(self) -> tuple[str, ...]:
        """Return warnings that make the current solid unsafe to export."""
        return tuple(warning for warning in self.warnings if warning in {"insufficient_base_thickness", "invalid_heightfield"})

    @property
    def exportable(self) -> bool:
        return not self.blocking_warnings


def analyze_heightfield(
    heightfield: np.ndarray,
    width_mm: float,
    depth_mm: float,
    base_thickness_mm: float,
    relief_mode: str = "positive",
    *,
    minimum_feature_width_mm: float = 0.4,
    maximum_slope_degrees: float = 65.0,
    high_frequency_limit: float = 0.15,
    profile: FabricationProfile | None = None,
    cancel_check=None,
) -> FabricationMetrics:
    """Estimate physical risks without claiming printer-specific guarantees.

    The feature-width value is a raster resolution estimate: two samples are
    required to represent a feature. It is deliberately reported as a resolved
    width, not as a guarantee that every feature in the field is printable.
    """
    if profile is not None:
        profile.validate()
        minimum_feature_width_mm = profile.minimum_feature_width_mm
        maximum_slope_degrees = profile.maximum_slope_degrees
        high_frequency_limit = profile.high_frequency_limit
    values = np.asarray(heightfield, dtype=np.float32)
    check_cancelled(cancel_check)
    if values.ndim != 2 or min(values.shape, default=0) < 2 or not np.isfinite(values).all():
        return FabricationMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, float("inf"), float("inf"), ("invalid_heightfield",))
    if not np.isfinite([width_mm, depth_mm, base_thickness_mm, minimum_feature_width_mm, maximum_slope_degrees, high_frequency_limit]).all():
        raise ValueError("Fabrication dimensions and thresholds must be finite")
    if width_mm <= 0 or depth_mm <= 0 or base_thickness_mm <= 0:
        raise ValueError("Fabrication dimensions and base thickness must be positive")
    if relief_mode not in {"positive", "negative"}:
        raise ValueError("Relief mode must be positive or negative")
    if minimum_feature_width_mm <= 0 or not 0 < maximum_slope_degrees < 90 or high_frequency_limit < 0:
        raise ValueError("Fabrication thresholds are invalid")

    rows, columns = values.shape
    spacing_x = width_mm / (columns - 1)
    spacing_y = depth_mm / (rows - 1)
    sample_spacing = min(spacing_x, spacing_y)
    resolved_width = 2.0 * sample_spacing
    signed = values if relief_mode == "positive" else -values
    minimum = float(signed.min())
    maximum = float(signed.max())
    relief_range = maximum - minimum
    minimum_wall = base_thickness_mm + minimum

    gradient_y, gradient_x = np.gradient(signed, spacing_y, spacing_x)
    check_cancelled(cancel_check)
    slope = np.degrees(np.arctan(np.hypot(gradient_x, gradient_y)))
    maximum_slope = float(np.max(slope))

    if relief_range > 0:
        laplacian = np.zeros_like(signed)
        if columns > 2:
            laplacian[:, 1:-1] += np.abs(signed[:, :-2] - 2.0 * signed[:, 1:-1] + signed[:, 2:])
        if rows > 2:
            laplacian[1:-1, :] += np.abs(signed[:-2, :] - 2.0 * signed[1:-1, :] + signed[2:, :])
        high_frequency_ratio = float(np.mean(laplacian) / relief_range)
    else:
        high_frequency_ratio = 0.0
    check_cancelled(cancel_check)

    warnings: list[str] = []
    if minimum_wall <= 0:
        warnings.append("insufficient_base_thickness")
    if resolved_width < minimum_feature_width_mm:
        warnings.append("insufficient_sampling_for_feature_width")
    if maximum_slope > maximum_slope_degrees:
        warnings.append("surface_slope_exceeds_limit")
    if high_frequency_ratio > high_frequency_limit:
        warnings.append("high_frequency_detail")
    return FabricationMetrics(
        minimum_height_mm=minimum,
        maximum_height_mm=maximum,
        relief_range_mm=relief_range,
        minimum_wall_mm=minimum_wall,
        sample_spacing_mm=sample_spacing,
        minimum_resolved_feature_width_mm=resolved_width,
        maximum_slope_degrees=maximum_slope,
        high_frequency_ratio=high_frequency_ratio,
        warnings=tuple(warnings),
    )
