"""Worker-safe evaluation of serialized V2 field sources."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from clayfield.core.cancellation import check_cancelled
from clayfield.field.composition import compose_fields
from clayfield.field.generators import (
    CellularAutomataParameters,
    ChladniParameters,
    CrackParameters,
    ErosionParameters,
    FlowFieldParameters,
    GaborParameters,
    GaussianPeakParameters,
    JuliaParameters,
    LSystemParameters,
    MandelbrotParameters,
    MoireParameters,
    NoiseParameters,
    PhyllotaxisParameters,
    ReactionDiffusionParameters,
    RidgedNoiseParameters,
    SdfParameters,
    SpectralParameters,
    SuperformulaParameters,
    TilingParameters,
    VoronoiParameters,
    WarpedNoiseParameters,
    WaveParameters,
    generate_cellular_automata_field,
    generate_chladni_field,
    generate_crack_field,
    generate_eroded_field,
    generate_flow_field,
    generate_fractal_noise,
    generate_gabor_field,
    generate_gaussian_peaks_field,
    generate_julia_field,
    generate_lsystem_field,
    generate_mandelbrot_field,
    generate_moire_field,
    generate_penrose_field,
    generate_phyllotaxis_field,
    generate_reaction_diffusion_field,
    generate_ridged_noise,
    generate_sdf_field,
    generate_spectral_field,
    generate_superformula_field,
    generate_truchet_field,
    generate_voronoi_field,
    generate_warped_noise,
    generate_wave_field,
)
from clayfield.field.model import FieldMetadata, NormalizedField
from clayfield.field.persistence import PipelineSnapshot
from clayfield.field.pipeline import FieldPipelineResult, evaluate_field_pipeline
from clayfield.field.processing import FieldProcessingSettings, process_field, resize_field
from clayfield.field.qfractalnow import render_qfractalnow_config
from clayfield.terrain.mapping import MappingSettings


def _generate_source(source, shape, external_fields=None, cancel_check=None):
    if source.source_type == "heightmap":
        external_fields = external_fields or {}
        field = external_fields.get(source.content_hash)
        if field is None:
            raise ValueError("External field data is not available for this source")
        return resize_field(field, (shape[1], shape[0])) if field.shape != shape else field
    if source.source_type == "qfractalnow_config":
        return render_qfractalnow_config(source.parameters.get("config_text", ""), shape, cancel_check=cancel_check)
    if source.source_type == "fractal_noise":
        return generate_fractal_noise(shape, NoiseParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "wave_interference":
        return generate_wave_field(shape, WaveParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "mandelbrot":
        return generate_mandelbrot_field(shape, MandelbrotParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "voronoi":
        return generate_voronoi_field(shape, VoronoiParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "ridged_noise":
        return generate_ridged_noise(shape, RidgedNoiseParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "warped_noise":
        return generate_warped_noise(shape, WarpedNoiseParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "sdf":
        return generate_sdf_field(shape, SdfParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "chladni":
        return generate_chladni_field(shape, ChladniParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "spectral":
        return generate_spectral_field(shape, SpectralParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "reaction_diffusion":
        return generate_reaction_diffusion_field(
            shape, ReactionDiffusionParameters(**source.parameters), cancel_check=cancel_check
        )
    if source.source_type == "phyllotaxis":
        return generate_phyllotaxis_field(shape, PhyllotaxisParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "cellular_automata":
        return generate_cellular_automata_field(
            shape, CellularAutomataParameters(**source.parameters), cancel_check=cancel_check
        )
    if source.source_type == "flow_field":
        return generate_flow_field(shape, FlowFieldParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "erosion":
        return generate_eroded_field(shape, ErosionParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "lsystem":
        return generate_lsystem_field(shape, LSystemParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "cracks":
        return generate_crack_field(shape, CrackParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "penrose":
        return generate_penrose_field(shape, TilingParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "truchet":
        return generate_truchet_field(shape, TilingParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "superformula":
        return generate_superformula_field(
            shape, SuperformulaParameters(**source.parameters), cancel_check=cancel_check
        )
    if source.source_type == "gaussian_peaks":
        return generate_gaussian_peaks_field(
            shape, GaussianPeakParameters(**source.parameters), cancel_check=cancel_check
        )
    if source.source_type == "julia":
        return generate_julia_field(shape, JuliaParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "moire":
        return generate_moire_field(shape, MoireParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "gabor":
        return generate_gabor_field(shape, GaborParameters(**source.parameters), cancel_check=cancel_check)
    if source.source_type == "radial_mask":
        check_cancelled(cancel_check)
        parameters = source.parameters
        rows, columns = shape
        x = np.linspace(0.0, 1.0, columns, dtype=np.float32)
        y = np.linspace(0.0, 1.0, rows, dtype=np.float32)
        distance = np.hypot(
            x[None, :] - float(parameters.get("center_x", 0.5)), y[:, None] - float(parameters.get("center_y", 0.5))
        )
        inner = float(parameters.get("inner_radius", 0.0))
        outer = float(parameters.get("outer_radius", 0.5))
        if outer <= inner:
            raise ValueError("Radial mask outer radius must exceed inner radius")
        mask = np.clip((outer - distance) / (outer - inner), 0.0, 1.0)
        if bool(parameters.get("invert", False)):
            mask = 1.0 - mask
        check_cancelled(cancel_check)
        return NormalizedField(mask.astype(np.float32), FieldMetadata("radial_mask", "radial_mask", "1"))
    raise ValueError(f"Serialized source type is not a native procedural source: {source.source_type}")


def evaluate_serialized_pipeline(
    snapshot: PipelineSnapshot,
    shape: tuple[int, int],
    *,
    primary_field: NormalizedField | None = None,
    external_fields: dict[str, NormalizedField] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
) -> FieldPipelineResult:
    """Evaluate a validated snapshot without accessing Qt or mutable UI state."""
    snapshot.validate()
    check_cancelled(cancel_check)
    if primary_field is not None:
        field = resize_field(primary_field, (shape[1], shape[0])) if primary_field.shape != shape else primary_field
    else:
        field = _generate_source(snapshot.source, shape, external_fields, cancel_check)
    if progress_callback is not None:
        progress_callback(50, "Generated normalized source field")
    check_cancelled(cancel_check)
    composition = snapshot.composition or {}
    if snapshot.secondary_source is not None and composition.get("enabled", False):
        secondary = _generate_source(snapshot.secondary_source, shape, external_fields, cancel_check)
        secondary = process_field(
            secondary, FieldProcessingSettings(**snapshot.secondary_processing), cancel_check=cancel_check
        )
        mask = (
            _generate_source(snapshot.mask_source, shape, external_fields, cancel_check)
            if snapshot.mask_source is not None
            else None
        )
        field = compose_fields(
            field,
            secondary,
            operation=composition.get("operation", "blend"),
            amount=float(composition.get("amount", 1.0)),
            mask=mask,
            range_policy=composition.get("range_policy", "clip"),
        )
        check_cancelled(cancel_check)
    result = evaluate_field_pipeline(
        field,
        processing=FieldProcessingSettings(**snapshot.processing),
        mapping=MappingSettings(**snapshot.mapping),
        cancel_check=cancel_check,
    )
    if progress_callback is not None:
        progress_callback(100, "Mapped physical heightfield")
    check_cancelled(cancel_check)
    return result
