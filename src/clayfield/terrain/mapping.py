"""V2 normalized-field to physical-height mapping."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from clayfield.field.model import NormalizedField
from clayfield.image.curves import apply_curve
from clayfield.terrain.heightfield import PhysicalDimensions


@dataclass(frozen=True)
class MappingSettings:
    """Explicit physical mapping controls for a normalized field."""

    minimum_height_mm: float = 0.0
    maximum_height_mm: float = 5.0
    gamma: float = 1.0
    inverted: bool = False
    clamp_min: float = 0.0
    clamp_max: float = 1.0
    edge_falloff: float = 0.0
    edge_strength: float = 1.0
    edge_falloff_mode: str = "linear"
    offset_mm: float = 0.0
    scale: float = 1.0
    mapping_curve_points: tuple[tuple[float, float], ...] = ((0.0, 0.0), (1.0, 1.0))

    def validate(self) -> None:
        dimensions = PhysicalDimensions(minimum_height_mm=self.minimum_height_mm, maximum_height_mm=self.maximum_height_mm)
        dimensions.validate()
        values = (self.gamma, self.clamp_min, self.clamp_max, self.edge_falloff, self.edge_strength, self.offset_mm, self.scale)
        if not np.isfinite(values).all():
            raise ValueError("Mapping settings must be finite")
        if self.gamma <= 0 or self.scale <= 0 or not 0 <= self.clamp_min <= self.clamp_max <= 1:
            raise ValueError("Mapping gamma or clamp range is invalid")
        if not 0 <= self.edge_falloff <= 1 or not 0 <= self.edge_strength <= 1:
            raise ValueError("Edge mapping settings must be between 0 and 1")
        if self.edge_falloff_mode not in {"linear", "smoothstep"}:
            raise ValueError("Edge falloff mode must be linear or smoothstep")
        if not self.mapping_curve_points:
            raise ValueError("Mapping curve must contain points")
        if any(not 0 <= x <= 1 or not 0 <= y <= 1 for x, y in self.mapping_curve_points):
            raise ValueError("Mapping curve points must be normalized")


def map_field_to_physical(field: NormalizedField, settings: MappingSettings | None = None) -> np.ndarray:
    """Map a normalized field to millimeters using the V2 stage contract."""
    settings = settings or MappingSettings()
    settings.validate()
    values = field.values.copy()
    if settings.inverted:
        values = 1.0 - values
    values = np.power(values, 1.0 / settings.gamma, dtype=np.float32)
    values = apply_curve(values, list(settings.mapping_curve_points))
    values = np.clip(values, settings.clamp_min, settings.clamp_max)
    if settings.edge_falloff > 0:
        rows, columns = values.shape
        row_distance = np.minimum(np.arange(rows), np.arange(rows)[::-1]) / max(1, rows - 1)
        column_distance = np.minimum(np.arange(columns), np.arange(columns)[::-1]) / max(1, columns - 1)
        distance = np.minimum(row_distance[:, None], column_distance[None, :])
        mask = np.clip(distance / max(1e-6, settings.edge_falloff / 2.0), 0.0, 1.0)
        if settings.edge_falloff_mode == "smoothstep":
            mask = mask * mask * (3.0 - 2.0 * mask)
        values *= 1.0 - settings.edge_strength + settings.edge_strength * mask
    dimensions = PhysicalDimensions(minimum_height_mm=settings.minimum_height_mm, maximum_height_mm=settings.maximum_height_mm)
    result = dimensions.minimum_height_mm + values * (dimensions.maximum_height_mm - dimensions.minimum_height_mm)
    result = result * settings.scale + settings.offset_mm
    return np.asarray(result, dtype=np.float32)
