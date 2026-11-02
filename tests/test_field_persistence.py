"""Tests for V2 source descriptors and worker-safe pipeline evaluation."""

import threading

import numpy as np
import pytest

from clayfield.app.cancellation import WorkerCancelled
from clayfield.field import (
    FieldProcessingSettings,
    PipelineSnapshot,
    SourceDescriptor,
    evaluate_serialized_pipeline,
    pipeline_cache_key,
)
from clayfield.terrain.mapping import MappingSettings


def noise_snapshot() -> PipelineSnapshot:
    source = SourceDescriptor(
        source_type="fractal_noise",
        algorithm="value_fbm",
        algorithm_version="1",
        seed=42,
        parameters={"seed": 42, "base_frequency": 2.0, "octaves": 4, "persistence": 0.5, "lacunarity": 2.0, "amplitude": 1.0, "normalization": "auto", "tileable": False},
    )
    return PipelineSnapshot.from_settings(
        source,
        FieldProcessingSettings(resize=(20, 16)),
        MappingSettings(maximum_height_mm=5.0),
    )


def test_snapshot_round_trip_is_json_safe() -> None:
    snapshot = noise_snapshot()
    restored = PipelineSnapshot.from_dict(snapshot.to_dict())
    assert restored.to_dict() == snapshot.to_dict()


def test_snapshot_rejects_unsupported_pipeline_algorithm_version() -> None:
    snapshot = noise_snapshot().to_dict()
    snapshot["algorithm_versions"]["mapping"] = "99"
    with pytest.raises(ValueError, match="mapping"):
        PipelineSnapshot.from_dict(snapshot)


def test_pipeline_cache_key_changes_with_shape_or_parameters() -> None:
    snapshot = noise_snapshot()
    changed = PipelineSnapshot.from_dict({**snapshot.to_dict(), "source": {**snapshot.to_dict()["source"], "seed": 43, "parameters": {**snapshot.to_dict()["source"]["parameters"], "seed": 43}}})
    assert pipeline_cache_key(snapshot, (32, 32)) != pipeline_cache_key(snapshot, (16, 16))
    assert pipeline_cache_key(snapshot, (32, 32)) != pipeline_cache_key(changed, (32, 32))


def test_serialized_pipeline_is_reproducible_and_reports_progress() -> None:
    progress = []
    snapshot = noise_snapshot()
    first = evaluate_serialized_pipeline(snapshot, (32, 32), progress_callback=lambda percent, message: progress.append((percent, message)))
    second = evaluate_serialized_pipeline(snapshot, (32, 32))
    np.testing.assert_array_equal(first.physical_heightfield, second.physical_heightfield)
    assert progress == [(50, "Generated normalized source field"), (100, "Mapped physical heightfield")]


def test_serialized_secondary_field_and_radial_mask_are_composed() -> None:
    primary = noise_snapshot().source
    secondary = SourceDescriptor(
        source_type="wave_interference",
        algorithm="wave_interference",
        algorithm_version="1",
        parameters={"mode": "radial", "radial_frequency": 4.0, "radial_phase": 0.0, "center_x": 0.5, "center_y": 0.5, "output_amplitude": 1.0, "frequency_x": 3.0, "frequency_y": 3.0, "amplitude_x": 1.0, "amplitude_y": 1.0, "phase_x": 0.0, "phase_y": 0.0, "normalization": "auto"},
    )
    mask = SourceDescriptor(source_type="radial_mask", parameters={"inner_radius": 0.1, "outer_radius": 0.7})
    snapshot = PipelineSnapshot.from_settings(
        primary,
        mapping=MappingSettings(maximum_height_mm=5.0),
        secondary_source=secondary,
        mask_source=mask,
        composition={"enabled": True, "operation": "blend", "amount": 0.5, "range_policy": "clip"},
    )
    result = evaluate_serialized_pipeline(snapshot, (16, 16))
    assert result.normalized_field.shape == (16, 16)
    assert result.physical_heightfield.max() <= 5.0


def test_external_secondary_field_is_injected_at_pipeline_resolution() -> None:
    primary = noise_snapshot().source
    external = SourceDescriptor(source_type="heightmap", content_hash="external-hash", parameters={"filename": "external.png"})
    snapshot = PipelineSnapshot.from_settings(
        primary,
        mapping=MappingSettings(maximum_height_mm=5.0),
        secondary_source=external,
        composition={"enabled": True, "operation": "blend", "amount": 0.5, "range_policy": "clip"},
    )
    from clayfield.field import FieldMetadata, NormalizedField
    external_field = NormalizedField(np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32), FieldMetadata("external", "fixture"))
    result = evaluate_serialized_pipeline(snapshot, (12, 12), external_fields={"external-hash": external_field})
    assert result.normalized_field.shape == (12, 12)


def test_serialized_pipeline_rejects_external_source_without_imported_data() -> None:
    snapshot = PipelineSnapshot.from_settings(SourceDescriptor(source_type="image"))
    with pytest.raises(ValueError, match="native procedural"):
        evaluate_serialized_pipeline(snapshot, (8, 8))


def test_serialized_pipeline_honors_cancellation() -> None:
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(WorkerCancelled):
        evaluate_serialized_pipeline(noise_snapshot(), (32, 32), cancel_check=cancelled.is_set)
