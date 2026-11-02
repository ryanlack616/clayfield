"""Deterministic processing stages for normalized V2 fields."""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from clayfield.app.cancellation import check_cancelled
from clayfield.field.model import NormalizedField
from clayfield.image.curves import apply_curve
from clayfield.image.filters import adjust_brightness_contrast, gaussian_blur, sharpen, threshold
from clayfield.image.levels import apply_levels


FIELD_PROCESSING_STAGE_ORDER = (
    "source_resampling",
    "levels",
    "curve",
    "brightness_contrast",
    "blur",
    "sharpen",
    "threshold",
    "range_policy",
)


@dataclass(frozen=True)
class FieldProcessingSettings:
    """Settings for the explicit V2 field-processing stage sequence."""

    resize: tuple[int, int] | None = None
    black_point: float = 0.0
    input_gamma: float = 1.0
    white_point: float = 1.0
    output_black: float = 0.0
    output_white: float = 1.0
    curve_points: tuple[tuple[float, float], ...] = ((0.0, 0.0), (1.0, 1.0))
    curve_interpolation: str = "linear"
    brightness: float = 0.0
    contrast: float = 1.0
    blur_radius: float = 0.0
    sharpen_amount: float = 0.0
    threshold_enabled: bool = False
    threshold_cutoff: float = 0.5
    inverted: bool = False
    range_policy: str = "clip"
    stage_order: tuple[str, ...] = field(default_factory=lambda: FIELD_PROCESSING_STAGE_ORDER)

    def validate(self) -> None:
        if self.resize is not None:
            if len(self.resize) != 2 or any(isinstance(size, bool) or not isinstance(size, int) or size < 2 for size in self.resize):
                raise ValueError("Field resize must contain two dimensions of at least 2")
        if self.stage_order != FIELD_PROCESSING_STAGE_ORDER:
            raise ValueError("V2 field processing stage order cannot be changed")
        if self.range_policy not in {"clip", "normalize"}:
            raise ValueError("Field range policy must be clip or normalize")


def resize_field(field: NormalizedField, resolution: tuple[int, int]) -> NormalizedField:
    """Resample a field as ``(width, height)`` using area filtering when shrinking."""
    if len(resolution) != 2 or any(isinstance(size, bool) or not isinstance(size, int) or size < 2 for size in resolution):
        raise ValueError("Field resolution must contain two dimensions of at least 2")
    width, height = resolution
    values = field.values
    interpolation = cv2.INTER_AREA if width <= values.shape[1] and height <= values.shape[0] else cv2.INTER_LINEAR
    resized = cv2.resize(values, (width, height), interpolation=interpolation)
    return NormalizedField(np.clip(resized, 0.0, 1.0).astype(np.float32), field.metadata)


def _apply_range_policy(values: np.ndarray, policy: str) -> np.ndarray:
    if policy == "clip":
        return np.clip(values, 0.0, 1.0).astype(np.float32)
    minimum, maximum = float(values.min()), float(values.max())
    return ((values - minimum) / (maximum - minimum) if maximum > minimum else np.zeros_like(values)).astype(np.float32)


def process_field(field: NormalizedField, settings: FieldProcessingSettings | None = None, *, cancel_check=None) -> NormalizedField:
    """Apply the V2 processing stages in their fixed, documented order."""
    settings = settings or FieldProcessingSettings()
    settings.validate()
    check_cancelled(cancel_check)
    working = resize_field(field, settings.resize) if settings.resize is not None else field
    values = working.values
    values = apply_levels(
        values,
        settings.black_point,
        settings.input_gamma,
        settings.white_point,
        settings.output_black,
        settings.output_white,
    )
    check_cancelled(cancel_check)
    values = apply_curve(values, list(settings.curve_points), settings.curve_interpolation)
    values = adjust_brightness_contrast(values, settings.brightness, settings.contrast)
    check_cancelled(cancel_check)
    values = gaussian_blur(values, settings.blur_radius)
    values = sharpen(values, settings.sharpen_amount) if settings.sharpen_amount else values
    check_cancelled(cancel_check)
    if settings.threshold_enabled:
        values = threshold(values, settings.threshold_cutoff)
    values = _apply_range_policy(values, settings.range_policy)
    if settings.inverted:
        values = 1.0 - values
    check_cancelled(cancel_check)
    return NormalizedField(values, working.metadata)
