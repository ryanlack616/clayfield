"""Regression tests for the Stage 2 shared resource budgets."""

import warnings

import numpy as np
import pytest

from clayfield.field.generators import (
    CellularAutomataParameters,
    ErosionParameters,
    MandelbrotParameters,
    NoiseParameters,
    PhyllotaxisParameters,
    ReactionDiffusionParameters,
    VoronoiParameters,
    _generator_workload,
)
from clayfield.field.pipeline import FieldPipelineResult
from clayfield.field.model import FieldMetadata, NormalizedField
from clayfield.image.pipeline import AdjustmentCache, DEFAULT_ADJUSTMENT_CACHE_BYTES
from clayfield.resource_budget import (
    DEFAULT_BUDGET,
    MAX_ABSOLUTE_RESOLUTION_DIMENSION,
    ResourceBudget,
    estimate_heightfield,
    estimate_mesh_export,
    preflight_heightfield,
    preflight_mesh_export,
    recommended_resolution_for_budget,
)


def test_heightfield_preflight_accepts_large_legitimate_resolution() -> None:
    estimate = preflight_heightfield(16384, 16384)
    assert estimate.total_cpu_bytes < DEFAULT_BUDGET.cpu_limit_bytes


def test_heightfield_preflight_rejects_absolute_ceiling() -> None:
    with pytest.raises(ValueError, match="absolute allocation limit"):
        preflight_heightfield(MAX_ABSOLUTE_RESOLUTION_DIMENSION + 1, 16384)


def test_heightfield_preflight_rejects_budget_overrun() -> None:
    with pytest.raises(ValueError, match="configured CPU budget"):
        preflight_heightfield(16384, 16384, stages=64)


def test_mesh_preflight_accepts_default_2048_export() -> None:
    estimate = preflight_mesh_export(2048, 2048)
    assert estimate.total_cpu_bytes < DEFAULT_BUDGET.cpu_limit_bytes


def test_mesh_preflight_accepts_4096_export() -> None:
    # Measured validation peak at 4096x4096 is about 14 GiB on the 32 GB host,
    # so this resolution must fit the configured CPU budget.
    estimate = preflight_mesh_export(4096, 4096)
    assert estimate.total_cpu_bytes < DEFAULT_BUDGET.cpu_limit_bytes


def test_mesh_preflight_rejects_8192_export() -> None:
    with pytest.raises(ValueError, match="reduce export resolution"):
        preflight_mesh_export(8192, 8192)


def test_mesh_estimate_includes_heightfield_and_container() -> None:
    plain = estimate_mesh_export(512, 512)
    container = estimate_mesh_export(512, 512, container=True)
    assert container.total_cpu_bytes > plain.total_cpu_bytes


def test_recommended_resolution_for_budget_fits() -> None:
    rows, columns = recommended_resolution_for_budget(8192, 8192, DEFAULT_BUDGET.cpu_limit_bytes)
    assert max(rows, columns) < 8192
    assert estimate_mesh_export(rows, columns).total_cpu_bytes <= DEFAULT_BUDGET.cpu_limit_bytes


def test_recommended_resolution_for_container_budget_fits() -> None:
    rows, columns = recommended_resolution_for_budget(
        8192, 8192, DEFAULT_BUDGET.cpu_limit_bytes, container=True
    )
    assert max(rows, columns) < 8192
    assert (
        estimate_mesh_export(rows, columns, container=True).total_cpu_bytes
        <= DEFAULT_BUDGET.cpu_limit_bytes
    )


def test_adjustment_cache_evicts_by_bytes() -> None:
    cache = AdjustmentCache(max_bytes=2 * 32 * 32 * 4)
    source = np.linspace(0, 1, 32 * 32, dtype=np.float32).reshape(32, 32)
    settings = {
        "inverted": False,
        "Black point": 0.0,
        "Gamma": 1.0,
        "White point": 1.0,
        "Output black": 0.0,
        "Output white": 1.0,
        "Brightness": 0.0,
        "Contrast": 1.0,
        "Blur": 0.0,
        "Sharpen": 0.0,
        "threshold_enabled": False,
        "Threshold": 0.5,
        "Curve interpolation": "linear",
    }
    cache.apply(source, settings, [(0.0, 0.0), (1.0, 1.0)])
    assert cache._total_bytes <= cache._max_bytes
    assert 1 <= len(cache._stages) <= 2


def test_adjustment_cache_clear_releases_stages() -> None:
    cache = AdjustmentCache(max_bytes=DEFAULT_ADJUSTMENT_CACHE_BYTES)
    source = np.zeros((8, 8), dtype=np.float32)
    cache.apply(source, {}, [])
    assert cache._stages
    cache.clear()
    assert not cache._stages
    assert cache._total_bytes == 0


def test_adjustment_cache_rejects_invalid_budget() -> None:
    with pytest.raises(ValueError):
        AdjustmentCache(max_bytes=0)


def test_voronoi_high_cell_density_warns_at_soft_limit() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        estimate = _generator_workload((4096, 4096), VoronoiParameters(cell_density=200))
    assert estimate is not None
    assert estimate.total_cpu_bytes < DEFAULT_BUDGET.cpu_limit_bytes
    assert any("element operations" in str(item.message) for item in caught)


def test_voronoi_extreme_cell_density_is_rejected() -> None:
    with pytest.raises(ValueError, match="hard work limit"):
        _generator_workload((16384, 16384), VoronoiParameters(cell_density=10000))


def test_reaction_diffusion_iterations_warn_at_soft_limit() -> None:
    # 8192 x 8192 x 5000 iterations x 4 ops is about 1.3e12 element operations,
    # which is above work_soft_units but still inside the memory budget.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        estimate = _generator_workload((8192, 8192), ReactionDiffusionParameters(iterations=5000))
    assert estimate is not None
    assert estimate.total_cpu_bytes < DEFAULT_BUDGET.cpu_limit_bytes
    assert estimate.work_units > DEFAULT_BUDGET.work_soft_units
    assert any("element operations" in str(item.message) for item in caught)


def test_reaction_diffusion_moderate_iterations_stay_quiet() -> None:
    # 1024 x 1024 x 5000 iterations is about 2.1e10 element operations: slow
    # enough to notice, well below the documented interactive soft limit.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        estimate = _generator_workload((1024, 1024), ReactionDiffusionParameters(iterations=5000))
    assert estimate is not None
    assert estimate.work_units < DEFAULT_BUDGET.work_soft_units
    assert not caught


def test_generator_work_hard_limit_is_configurable() -> None:
    budget = ResourceBudget(work_hard_units=1)
    with pytest.raises(ValueError, match="hard work limit"):
        _generator_workload((32, 32), NoiseParameters(), budget=budget)


def test_generator_preflight_rejects_absolute_ceiling() -> None:
    with pytest.raises(ValueError, match="absolute allocation limit"):
        _generator_workload((MAX_ABSOLUTE_RESOLUTION_DIMENSION + 1, 16384), PhyllotaxisParameters())


def test_generator_preflight_keeps_cheap_generators_quiet() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _generator_workload((32, 32), CellularAutomataParameters())
        _generator_workload((32, 32), ErosionParameters())
        _generator_workload((32, 32), MandelbrotParameters())
    assert not caught


def test_field_pipeline_result_marks_physical_array_read_only() -> None:
    values = np.linspace(0, 1, 16, dtype=np.float32).reshape(4, 4)
    result = FieldPipelineResult(
        NormalizedField(values.copy(), FieldMetadata("test", "test")),
        values,
        ("test",),
    )
    assert not result.physical_heightfield.flags.writeable
    assert result.minimum == pytest.approx(float(values.min()))
    assert result.maximum == pytest.approx(float(values.max()))
