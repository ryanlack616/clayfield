"""Authoritative V2 normalized-to-physical field pipeline."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from clayfield.field.model import NormalizedField
from clayfield.field.processing import FIELD_PROCESSING_STAGE_ORDER, FieldProcessingSettings, process_field
from clayfield.terrain.mapping import MappingSettings, map_field_to_physical


@dataclass(frozen=True)
class FieldPipelineResult:
    """Published outputs from one deterministic field pipeline evaluation."""

    normalized_field: NormalizedField
    physical_heightfield: np.ndarray
    stage_order: tuple[str, ...]

    def __post_init__(self) -> None:
        values = np.asarray(self.physical_heightfield, dtype=np.float32)
        if values.shape != self.normalized_field.shape or not np.isfinite(values).all():
            raise ValueError("Physical heightfield must match the normalized field and be finite")
        values = np.array(values, dtype=np.float32, copy=True)
        values.setflags(write=False)
        object.__setattr__(self, "physical_heightfield", values)


def evaluate_field_pipeline(
    source: NormalizedField,
    *,
    processing: FieldProcessingSettings | None = None,
    mapping: MappingSettings | None = None,
    cancel_check=None,
) -> FieldPipelineResult:
    """Process and physically map a source using the fixed V2 stage order."""
    processed = process_field(source, processing, cancel_check=cancel_check)
    physical = map_field_to_physical(processed, mapping)
    return FieldPipelineResult(processed, physical, FIELD_PROCESSING_STAGE_ORDER)
