"""Tests for V2 field composition and physical mapping."""

import numpy as np
import pytest

from clayfield.field import FieldMetadata, NormalizedField, compose_fields
from clayfield.field import NoiseParameters, generate_fractal_noise
from clayfield.geometry.mesh_generator import generate_solid_mesh
from clayfield.geometry.validation import validate_mesh
from clayfield.terrain.mapping import MappingSettings, map_field_to_physical


def field(values: list[list[float]]) -> NormalizedField:
    return NormalizedField(np.asarray(values, dtype=np.float32), FieldMetadata("test", "fixture"))


def test_masked_blend_only_changes_masked_samples() -> None:
    primary = field([[0.0, 0.0], [0.0, 0.0]])
    secondary = field([[1.0, 1.0], [1.0, 1.0]])
    mask = field([[0.0, 1.0], [0.0, 1.0]])
    result = compose_fields(primary, secondary, operation="blend", amount=1.0, mask=mask)
    np.testing.assert_allclose(result.values, [[0.0, 1.0], [0.0, 1.0]])


def test_addition_has_explicit_clip_or_normalize_policy() -> None:
    primary = field([[0.75, 0.75], [0.75, 0.75]])
    secondary = field([[0.75, 0.75], [0.75, 0.75]])
    clipped = compose_fields(primary, secondary, operation="add", amount=1.0)
    normalized = compose_fields(primary, secondary, operation="add", amount=1.0, range_policy="normalize")
    np.testing.assert_allclose(clipped.values, 1.0)
    np.testing.assert_allclose(normalized.values, 0.0)


def test_composition_rejects_shape_and_operation_errors() -> None:
    with pytest.raises(ValueError, match="same shape"):
        compose_fields(field([[0, 1], [0, 1]]), field([[0, 1, 0], [0, 1, 0]]))
    with pytest.raises(ValueError, match="Unsupported"):
        compose_fields(field([[0, 1], [0, 1]]), field([[0, 1], [0, 1]]), operation="warp")


def test_mapping_preserves_physical_range_and_falls_off_at_edges() -> None:
    source = field([[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]])
    result = map_field_to_physical(
        source,
        MappingSettings(minimum_height_mm=0.0, maximum_height_mm=5.0, edge_falloff=0.5),
    )
    assert result.dtype == np.float32
    assert result[0, 0] == 0.0
    assert result[1, 1] == 5.0


def test_composed_procedural_field_reaches_validated_fabrication_mesh() -> None:
    primary = generate_fractal_noise((16, 16), NoiseParameters(seed=42))
    secondary = generate_fractal_noise((16, 16), NoiseParameters(seed=7, base_frequency=4))
    combined = compose_fields(primary, secondary, operation="blend", amount=0.35)
    physical = map_field_to_physical(combined, MappingSettings(maximum_height_mm=5.0))
    mesh = generate_solid_mesh(physical, 100.0, 100.0, 3.0)
    report = validate_mesh(mesh)
    assert report.valid
    assert report.bounds_mm[0] == (-50.0, 50.0)
    assert report.bounds_mm[2] == (-50.0, 50.0)
    assert report.bounds_mm[1][0] == -3.0
    assert 0.0 < report.bounds_mm[1][1] <= 5.0
