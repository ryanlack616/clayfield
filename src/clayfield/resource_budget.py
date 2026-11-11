"""Shared memory and resource budgets for Clayfield workloads.

This module exists so that every generation, analysis, and export path uses the
same decoded-memory reasoning. It is a *planning* layer, not a fabrication
limit: the budgets below describe how much RAM/VRAM one workload may consume on
the target machine. They are deliberately expressed in bytes so legitimate
large workloads are accepted while impossible allocations are rejected before
they happen.

Target machine (documented, not enforced by hardware detection):
  * 32 GB system RAM  -> 21 GiB initial CPU budget, 0.85 safety margin

GPU work is bounded separately by the OpenGL driver's ``GL_MAX_TEXTURE_SIZE``
(see ``ui.viewport`` and ``ui.gpu_pipeline``); there is deliberately no
second, unenforced VRAM number here. A budget field that nothing reads is a
false promise, so GPU fields are not declared until a consumer enforces them.

The 16384 per-axis ceiling is an absolute *allocation* safety bound, not a
2048/4096 fabrication preset. It matches the common desktop GPU 2D texture
limit and the ~1 GiB size of one float32 plane at that resolution. It is not
environment-configurable because persisted project metadata is untrusted input.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from clayfield.geometry.estimates import estimate_solid_mesh

GIB = 1024**3
MIB = 1024**2

# Absolute, non-overridable per-axis allocation ceiling. This is the single
# definition; clayfield.app.project_io imports it and re-exports the same value,
# so archive metadata validation and in-memory workload preflight cannot drift.
MAX_ABSOLUTE_RESOLUTION_DIMENSION = 16384


@dataclass(frozen=True)
class ResourceBudget:
    """Configurable planning budget for one Clayfield workload.

    ``total_*`` describe the machine. ``initial_*`` are the bytes Clayfield may
    plan to use for one workload before the safety margin. ``safety_margin``
    leaves headroom for the OS, Qt, and other processes. These are planning
    values, not hard guarantees; the actual peak may exceed the estimate.
    """

    total_ram_bytes: int = 32 * GIB
    initial_ram_bytes: int = 21 * GIB
    safety_margin: float = 0.85
    max_dimension: int = MAX_ABSOLUTE_RESOLUTION_DIMENSION
    # Soft work threshold used for a warning. One "unit" is one scalar element
    # operation. At the ~1e9 element-operations/second this host sustains for
    # memory-bound NumPy array math, 1e12 units is roughly 15 minutes: long
    # enough to be worth a warning, short enough to still be an interactive
    # render rather than a batch job.
    work_soft_units: int = 1_000_000_000_000
    # Hard work threshold used for rejection. 1e14 is about 28 hours of NumPy
    # work at 1e9 element-operations/second: a workload this large cannot be a
    # legitimate interactive render, so it is refused rather than warned about.
    work_hard_units: int = 100_000_000_000_000

    @property
    def cpu_limit_bytes(self) -> int:
        """Bytes available to one CPU workload after the safety margin."""
        return int(self.initial_ram_bytes * self.safety_margin)


DEFAULT_BUDGET = ResourceBudget()


@dataclass(frozen=True)
class WorkloadEstimate:
    """Estimated memory for one workload.

    ``persistent_bytes`` is retained for the lifetime of the workload.
    ``temporary_cpu_bytes`` is peak transient CPU memory. ``gpu_bytes`` is peak
    VRAM. ``work_units`` is an element-operation count used only for warning.
    ``confidence`` is ``"formula"`` or ``"measured"``.
    """

    persistent_bytes: int
    temporary_cpu_bytes: int
    gpu_bytes: int = 0
    work_units: int = 0
    confidence: str = "formula"
    breakdown: dict[str, int] = field(default_factory=dict)

    @property
    def total_cpu_bytes(self) -> int:
        return self.persistent_bytes + self.temporary_cpu_bytes

    @property
    def total_cpu_mebibytes(self) -> float:
        return self.total_cpu_bytes / MIB

    @property
    def total_gpu_mebibytes(self) -> float:
        return self.gpu_bytes / MIB


def _check_dimensions(rows: int, columns: int) -> None:
    if isinstance(rows, bool) or isinstance(columns, bool):
        raise ValueError("Resolution dimensions must be integers")
    if not isinstance(rows, int) or not isinstance(columns, int):
        raise ValueError("Resolution dimensions must be integers")
    if rows < 2 or columns < 2:
        raise ValueError("Resolution dimensions must be at least 2 by 2")


def estimate_heightfield(
    rows: int,
    columns: int,
    *,
    dtype_bytes: int = 4,
    stages: int = 4,
) -> WorkloadEstimate:
    """Estimate CPU memory for heightfield generation/analysis.

    ``stages`` counts full-resolution temporary arrays kept alive during
    smoothing, edge falloff, noise injection, and mapping. Four stages is the
    observed peak in ``generate_physical_heightfield``; callers with a simpler
    path may pass a lower value.
    """
    _check_dimensions(rows, columns)
    if dtype_bytes < 1 or stages < 1:
        raise ValueError("Heightfield estimate requires positive dtype and stage counts")
    pixels = rows * columns
    heightfield_bytes = pixels * dtype_bytes
    stage_bytes = pixels * dtype_bytes * stages
    return WorkloadEstimate(
        persistent_bytes=heightfield_bytes,
        temporary_cpu_bytes=stage_bytes,
        work_units=pixels * stages,
        breakdown={
            "heightfield": heightfield_bytes,
            "heightfield_stages": stage_bytes,
        },
    )


def preflight_heightfield(
    rows: int,
    columns: int,
    *,
    budget: ResourceBudget = DEFAULT_BUDGET,
    stages: int = 4,
) -> WorkloadEstimate:
    """Reject a heightfield workload that exceeds the configured memory budget."""
    _check_dimensions(rows, columns)
    if max(rows, columns) > budget.max_dimension:
        raise ValueError(
            f"Heightfield resolution {rows} x {columns} exceeds the absolute "
            f"allocation limit of {budget.max_dimension} per axis"
        )
    estimate = estimate_heightfield(rows, columns, stages=stages)
    if estimate.total_cpu_bytes > budget.cpu_limit_bytes:
        raise ValueError(
            f"Heightfield resolution {rows} x {columns} requires approximately "
            f"{estimate.total_cpu_mebibytes:.0f} MiB; the configured CPU budget is "
            f"{budget.cpu_limit_bytes / MIB:.0f} MiB. Reduce the resolution or raise "
            f"the budget."
        )
    return estimate


def estimate_mesh_export(
    rows: int,
    columns: int,
    *,
    container: bool = False,
) -> WorkloadEstimate:
    """Estimate CPU memory for a solid-mesh export at ``rows x columns``.

    The mesh estimate's ``working_bytes`` already includes its persistent
    arrays. The heightfield and optional container terms are added separately
    so the peak covers generation, mesh construction, orientation, Trimesh
    validation, and export verification.
    """
    _check_dimensions(rows, columns)
    mesh = estimate_solid_mesh(rows, columns)
    heightfield = estimate_heightfield(rows, columns)
    container_bytes = rows * columns * 4 if container else 0
    working = mesh.working_bytes + heightfield.temporary_cpu_bytes + container_bytes
    return WorkloadEstimate(
        persistent_bytes=mesh.total_bytes + heightfield.persistent_bytes,
        temporary_cpu_bytes=working,
        work_units=mesh.triangle_count + heightfield.work_units,
        breakdown={
            "mesh_vertices": mesh.vertex_bytes,
            "mesh_faces": mesh.face_bytes,
            "mesh_working": mesh.working_bytes,
            "heightfield": heightfield.persistent_bytes,
            "heightfield_stages": heightfield.temporary_cpu_bytes,
            "container": container_bytes,
        },
    )


def preflight_mesh_export(
    rows: int,
    columns: int,
    *,
    budget: ResourceBudget = DEFAULT_BUDGET,
    container: bool = False,
) -> WorkloadEstimate:
    """Reject a mesh export workload that exceeds the configured memory budget."""
    _check_dimensions(rows, columns)
    if max(rows, columns) > budget.max_dimension:
        raise ValueError(
            f"Export resolution {rows} x {columns} exceeds the absolute "
            f"allocation limit of {budget.max_dimension} per axis"
        )
    estimate = estimate_mesh_export(rows, columns, container=container)
    if estimate.total_cpu_bytes > budget.cpu_limit_bytes:
        suggested_rows, suggested_columns = recommended_resolution_for_budget(
            rows, columns, budget.cpu_limit_bytes, budget=budget, container=container
        )
        raise ValueError(
            f"Mesh export requires approximately {estimate.total_cpu_mebibytes:.0f} MiB; "
            f"the configured CPU budget is {budget.cpu_limit_bytes / MIB:.0f} MiB. "
            f"reduce export resolution to approximately {suggested_columns} x "
            f"{suggested_rows} or lower, or raise the budget."
        )
    return estimate


def recommended_resolution_for_budget(
    rows: int,
    columns: int,
    max_bytes: int,
    *,
    budget: ResourceBudget = DEFAULT_BUDGET,
    container: bool = False,
) -> tuple[int, int]:
    """Return an aspect-preserving ``(rows, columns)`` whose export fits ``max_bytes``.

    Unlike a triangle-count cap, this targets decoded/working memory. The return
    value is row-major, matching :func:`estimate_mesh_export` and
    :func:`preflight_mesh_export`; callers that print a "width x height"
    resolution must print ``columns`` first. ``container`` mirrors the same flag
    on the estimate so the suggestion accounts for container walls. It is a
    *suggestion* for the error message; the caller decides whether to reduce.
    """
    _check_dimensions(rows, columns)
    if max_bytes <= 0:
        raise ValueError("Byte budget must be positive")
    current = estimate_mesh_export(rows, columns, container=container)
    if current.total_cpu_bytes <= max_bytes:
        return rows, columns
    # Memory scales roughly with rows*columns; use a square-root scale and then
    # walk down until the estimate fits. This keeps the aspect ratio.
    scale = (max_bytes / current.total_cpu_bytes) ** 0.5
    suggested_rows = max(2, int(rows * scale))
    suggested_columns = max(2, int(columns * scale))
    while estimate_mesh_export(suggested_rows, suggested_columns, container=container).total_cpu_bytes > max_bytes:
        if suggested_rows >= suggested_columns and suggested_rows > 2:
            suggested_rows -= 1
        elif suggested_columns > 2:
            suggested_columns -= 1
        else:
            break
    return suggested_rows, suggested_columns
