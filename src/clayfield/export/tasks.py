"""Cancellable background tasks for heightfield and mesh exports."""

from __future__ import annotations

from numbers import Integral, Real

from clayfield.app.cancellation import WorkerCancelled
from clayfield.export.heightmap import export_heightmap
from clayfield.export.orientation import orient_for_print
from clayfield.export.stl import export_stl
from clayfield.export.three_mf import export_3mf
from clayfield.field.persistence import PipelineSnapshot
from clayfield.field.workflow import evaluate_serialized_pipeline
from clayfield.geometry.estimates import estimate_solid_mesh, recommended_resolution
from clayfield.geometry.mesh_generator import generate_solid_mesh
from clayfield.geometry.container import ContainerSettings, prepare_container_heightfield
from clayfield.terrain.heightfield import PhysicalDimensions, generate_physical_heightfield
from clayfield.terrain.fabrication import FabricationMetrics, analyze_heightfield


MAX_ESTIMATED_WORKING_BYTES = 2 * 1024 * 1024 * 1024


def _check_cancel(cancel_check) -> None:
    if cancel_check and cancel_check():
        raise WorkerCancelled()


def _validate_resolution(resolution):
    if not isinstance(resolution, (tuple, list)) or len(resolution) != 2:
        raise ValueError("Export resolution must contain width and height")
    validated = []
    for value in resolution:
        if isinstance(value, bool) or not isinstance(value, (Integral, Real)):
            raise ValueError("Export resolution dimensions must be integer values")
        numeric = float(value)
        if not numeric.is_integer():
            raise ValueError("Export resolution dimensions must be integer values")
        if numeric < 2:
            raise ValueError("Export resolution dimensions must be at least 2")
        validated.append(int(numeric))
    return tuple(validated)


def export_mesh_task(
    image,
    dimensions,
    resolution,
    base_thickness_mm,
    relief_mode,
    path,
    file_type,
    smoothing_sigma=0.0,
    edge_falloff=0.0,
    inverted=False,
    mapping_gamma=1.0,
    noise_amplitude=0.0,
    noise_frequency=1.0,
    noise_seed=0,
    mapping_curve_points=None,
    edge_falloff_mode="linear",
    cancel_check=None,
    progress_callback=None,
    height_options=None,
    container_settings=None,
):
    _check_cancel(cancel_check)
    width, height = _validate_resolution(resolution)
    estimate = estimate_solid_mesh(height, width)
    if estimate.working_bytes > MAX_ESTIMATED_WORKING_BYTES:
        suggested_rows, suggested_columns = recommended_resolution(estimate.rows, estimate.columns, 8_000_000)
        raise ValueError(
            f"Mesh export requires approximately {estimate.working_mebibytes:.0f} MiB; "
            f"reduce export resolution to approximately {suggested_columns} × {suggested_rows} or lower before continuing"
        )
    if progress_callback:
        progress_callback(10, "Preparing heightfield")
    heightfield = generate_physical_heightfield(
        image, dimensions, (width, height), inverted, smoothing_sigma, edge_falloff,
        mapping_gamma, noise_amplitude, noise_frequency, noise_seed,
        mapping_curve_points, edge_falloff_mode, options=height_options,
    )
    _check_cancel(cancel_check)
    if progress_callback:
        progress_callback(45, "Heightfield ready")
    container = container_settings or ContainerSettings()
    heightfield, mesh_width, mesh_depth = prepare_container_heightfield(heightfield, dimensions.width_mm, dimensions.depth_mm, container, relief_mode=relief_mode)
    mesh = generate_solid_mesh(
        heightfield, mesh_width, mesh_depth, base_thickness_mm,
        relief_mode, cancel_check=cancel_check,
    )
    _check_cancel(cancel_check)
    mesh = orient_for_print(mesh)
    _check_cancel(cancel_check)
    if progress_callback:
        progress_callback(85, "Writing export file")
    if file_type == "stl":
        output = export_stl(mesh, path, cancel_check=cancel_check)
    elif file_type == "3mf":
        output = export_3mf(mesh, path, cancel_check=cancel_check)
    else:
        raise ValueError(f"Unsupported mesh export type: {file_type}")
    if progress_callback:
        progress_callback(100, "Export complete")
    return output


def export_heightmap_task(
    image,
    dimensions,
    resolution,
    path,
    bit_depth=16,
    smoothing_sigma=0.0,
    edge_falloff=0.0,
    inverted=False,
    mapping_gamma=1.0,
    noise_amplitude=0.0,
    noise_frequency=1.0,
    noise_seed=0,
    mapping_curve_points=None,
    edge_falloff_mode="linear",
    cancel_check=None,
    progress_callback=None,
    relief_mode="positive",
    height_options=None,
):
    width, height = _validate_resolution(resolution)
    if relief_mode not in {"positive", "negative"}:
        raise ValueError("Relief mode must be positive or negative")
    _check_cancel(cancel_check)
    if progress_callback:
        progress_callback(10, "Preparing heightfield")
    heightfield = generate_physical_heightfield(
        image, dimensions, (width, height), inverted, smoothing_sigma, edge_falloff,
        mapping_gamma, noise_amplitude, noise_frequency, noise_seed,
        mapping_curve_points, edge_falloff_mode, options=height_options,
    )
    if relief_mode == "negative":
        heightfield = -heightfield
    _check_cancel(cancel_check)
    if progress_callback:
        progress_callback(85, "Writing heightmap")
    output = export_heightmap(heightfield, path, bit_depth, cancel_check=cancel_check)
    if progress_callback:
        progress_callback(100, "Export complete")
    return output


def export_procedural_mesh_task(
    snapshot: PipelineSnapshot,
    dimensions,
    resolution,
    base_thickness_mm,
    relief_mode,
    path,
    file_type,
    *,
    external_fields=None,
    container_settings=None,
    cancel_check=None,
    progress_callback=None,
):
    """Regenerate a procedural field at export resolution and write a solid."""
    _check_cancel(cancel_check)
    width, height = _validate_resolution(resolution)
    estimate = estimate_solid_mesh(height, width)
    if estimate.working_bytes > MAX_ESTIMATED_WORKING_BYTES:
        suggested_rows, suggested_columns = recommended_resolution(estimate.rows, estimate.columns, 8_000_000)
        raise ValueError(
            f"Mesh export requires approximately {estimate.working_mebibytes:.0f} MiB; "
            f"reduce export resolution to approximately {suggested_columns} × {suggested_rows} or lower before continuing"
        )
    if progress_callback:
        progress_callback(10, "Generating procedural export field")
    result = evaluate_serialized_pipeline(snapshot, (height, width), external_fields=external_fields, cancel_check=cancel_check)
    _check_cancel(cancel_check)
    if progress_callback:
        progress_callback(45, "Heightfield ready")
    container = container_settings or ContainerSettings()
    heightfield, mesh_width, mesh_depth = prepare_container_heightfield(result.physical_heightfield, dimensions.width_mm, dimensions.depth_mm, container, relief_mode=relief_mode)
    mesh = generate_solid_mesh(
        heightfield,
        mesh_width,
        mesh_depth,
        base_thickness_mm,
        relief_mode,
        cancel_check=cancel_check,
    )
    _check_cancel(cancel_check)
    mesh = orient_for_print(mesh)
    if progress_callback:
        progress_callback(85, "Writing export file")
    if file_type == "stl":
        output = export_stl(mesh, path, cancel_check=cancel_check)
    elif file_type == "3mf":
        output = export_3mf(mesh, path, cancel_check=cancel_check)
    else:
        raise ValueError(f"Unsupported mesh export type: {file_type}")
    if progress_callback:
        progress_callback(100, "Export complete")
    return output


def export_procedural_heightmap_task(
    snapshot: PipelineSnapshot,
    resolution,
    path,
    bit_depth=16,
    *,
    external_fields=None,
    relief_mode="positive",
    cancel_check=None,
    progress_callback=None,
):
    """Regenerate a procedural field at export resolution and write a heightmap."""
    _check_cancel(cancel_check)
    width, height = _validate_resolution(resolution)
    if progress_callback:
        progress_callback(10, "Generating procedural export field")
    result = evaluate_serialized_pipeline(snapshot, (height, width), external_fields=external_fields, cancel_check=cancel_check)
    heightfield = -result.physical_heightfield if relief_mode == "negative" else result.physical_heightfield
    _check_cancel(cancel_check)
    if progress_callback:
        progress_callback(85, "Writing heightmap")
    output = export_heightmap(heightfield, path, bit_depth, cancel_check=cancel_check)
    if progress_callback:
        progress_callback(100, "Export complete")
    return output


def analyze_procedural_export_task(
    snapshot: PipelineSnapshot,
    resolution,
    width_mm: float,
    depth_mm: float,
    base_thickness_mm: float,
    relief_mode: str,
    *,
    external_fields=None,
    primary_field=None,
    profile=None,
    cancel_check=None,
    progress_callback=None,
) -> FabricationMetrics:
    """Analyze the exact regenerated field selected for procedural export."""
    _check_cancel(cancel_check)
    width, height = _validate_resolution(resolution)
    if progress_callback:
        progress_callback(15, "Generating final export field")
    result = evaluate_serialized_pipeline(
        snapshot,
        (height, width),
        primary_field=primary_field,
        external_fields=external_fields,
        cancel_check=cancel_check,
    )
    _check_cancel(cancel_check)
    display = -result.physical_heightfield if relief_mode == "negative" else result.physical_heightfield
    metrics = analyze_heightfield(display, width_mm, depth_mm, base_thickness_mm, "positive", profile=profile, cancel_check=cancel_check)
    if progress_callback:
        progress_callback(100, "Final export analysis ready")
    return metrics


def analyze_image_export_task(
    image,
    dimensions,
    resolution,
    base_thickness_mm,
    relief_mode,
    smoothing_sigma=0.0,
    edge_falloff=0.0,
    inverted=False,
    mapping_gamma=1.0,
    noise_amplitude=0.0,
    noise_frequency=1.0,
    noise_seed=0,
    mapping_curve_points=None,
    edge_falloff_mode="linear",
    *,
    height_options=None,
    profile=None,
    cancel_check=None,
    progress_callback=None,
) -> FabricationMetrics:
    """Analyze the exact regenerated field used by the V1 image export path."""
    _check_cancel(cancel_check)
    width, height = _validate_resolution(resolution)
    if progress_callback:
        progress_callback(15, "Generating final image export field")
    heightfield = generate_physical_heightfield(
        image,
        dimensions,
        (width, height),
        inverted,
        smoothing_sigma,
        edge_falloff,
        mapping_gamma,
        noise_amplitude,
        noise_frequency,
        noise_seed,
        mapping_curve_points,
        edge_falloff_mode,
        options=height_options,
    )
    _check_cancel(cancel_check)
    display = -heightfield if relief_mode == "negative" else heightfield
    metrics = analyze_heightfield(display, dimensions.width_mm, dimensions.depth_mm, base_thickness_mm, "positive", profile=profile, cancel_check=cancel_check)
    if progress_callback:
        progress_callback(100, "Final export analysis ready")
    return metrics
