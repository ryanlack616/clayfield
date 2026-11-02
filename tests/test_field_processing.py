"""Tests for the ordered V2 field processing pipeline."""

import numpy as np
import pytest

from clayfield.field import (
    FIELD_PROCESSING_STAGE_ORDER,
    FieldMetadata,
    FieldProcessingSettings,
    NormalizedField,
    evaluate_field_pipeline,
    process_field,
    resize_field,
)
from clayfield.terrain.mapping import MappingSettings


def source() -> NormalizedField:
    values = np.linspace(0.0, 1.0, 16, dtype=np.float32).reshape(4, 4)
    return NormalizedField(values, FieldMetadata("test", "fixture"))


def test_processing_order_and_resize_are_explicit() -> None:
    settings = FieldProcessingSettings(resize=(8, 6), brightness=0.1, contrast=1.2)
    result = process_field(source(), settings)
    assert FIELD_PROCESSING_STAGE_ORDER == settings.stage_order
    assert result.shape == (6, 8)
    assert result.values.dtype == np.float32
    assert np.isfinite(result.values).all()
    assert result.values.min() >= 0 and result.values.max() <= 1


def test_processing_can_normalize_after_tonal_operations() -> None:
    result = process_field(
        source(),
        FieldProcessingSettings(output_black=0.2, output_white=0.6, range_policy="normalize"),
    )
    np.testing.assert_allclose((result.values.min(), result.values.max()), (0.0, 1.0), atol=1e-6)


def test_resize_uses_width_then_height() -> None:
    result = resize_field(source(), (10, 6))
    assert result.shape == (6, 10)


def test_processing_rejects_stage_order_changes() -> None:
    with pytest.raises(ValueError, match="stage order"):
        FieldProcessingSettings(stage_order=("blur",)).validate()


def test_pipeline_publishes_normalized_and_physical_outputs() -> None:
    result = evaluate_field_pipeline(
        source(),
        processing=FieldProcessingSettings(resize=(8, 8)),
        mapping=MappingSettings(maximum_height_mm=5.0),
    )
    assert result.normalized_field.shape == (8, 8)
    assert result.physical_heightfield.shape == (8, 8)
    assert result.stage_order == FIELD_PROCESSING_STAGE_ORDER
    assert result.physical_heightfield.flags.writeable is False
    assert float(result.physical_heightfield.max()) <= 5.0
