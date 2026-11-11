"""Tests for the V2 deterministic normalized field foundation."""

import numpy as np
import pytest

from clayfield.app.cancellation import WorkerCancelled
from clayfield.field import (
    CellularAutomataParameters,
    ChladniParameters,
    ContourParameters,
    CrackParameters,
    ErosionParameters,
    FieldMetadata,
    FlowFieldParameters,
    LSystemParameters,
    MandelbrotParameters,
    NoiseParameters,
    NormalizedField,
    PhyllotaxisParameters,
    ReactionDiffusionParameters,
    RidgedNoiseParameters,
    SdfParameters,
    SpectralParameters,
    VoronoiParameters,
    WarpedNoiseParameters,
    WaveParameters,
    apply_contours,
    generate_cellular_automata_field,
    generate_chladni_field,
    generate_crack_field,
    generate_eroded_field,
    generate_flow_field,
    generate_fractal_noise,
    generate_lsystem_field,
    generate_mandelbrot_field,
    generate_phyllotaxis_field,
    generate_reaction_diffusion_field,
    generate_ridged_noise,
    generate_sdf_field,
    generate_spectral_field,
    generate_voronoi_field,
    generate_warped_noise,
    generate_wave_field,
)
from clayfield.geometry.mesh_generator import generate_solid_mesh
from clayfield.geometry.validation import validate_mesh


def test_noise_is_deterministic_and_immutable() -> None:
    parameters = NoiseParameters(seed=42, base_frequency=2.0, octaves=5, persistence=0.55)
    first = generate_fractal_noise((32, 40), parameters)
    second = generate_fractal_noise((32, 40), parameters)
    np.testing.assert_array_equal(first.values, second.values)
    assert first.values.dtype == np.float32
    assert first.values.flags.writeable is False
    assert first.metadata.source_type == "fractal_noise"


def test_noise_seed_and_resolution_change_the_field() -> None:
    first = generate_fractal_noise((32, 32), NoiseParameters(seed=1))
    changed_seed = generate_fractal_noise((32, 32), NoiseParameters(seed=2))
    changed_shape = generate_fractal_noise((24, 40), NoiseParameters(seed=1))
    assert not np.array_equal(first.values, changed_seed.values)
    assert changed_shape.shape == (24, 40)


def test_fixed_noise_amplitude_changes_dynamic_range() -> None:
    low = generate_fractal_noise((32, 32), NoiseParameters(amplitude=0.2, normalization="fixed"))
    high = generate_fractal_noise((32, 32), NoiseParameters(amplitude=0.8, normalization="fixed"))
    assert high.values.max() - high.values.min() > low.values.max() - low.values.min()


def test_planar_and_radial_wave_fields_are_bounded_and_reproducible() -> None:
    planar = generate_wave_field((24, 32), WaveParameters(frequency_x=2, frequency_y=3))
    radial = generate_wave_field((24, 32), WaveParameters(mode="radial", radial_frequency=4))
    repeat = generate_wave_field((24, 32), WaveParameters(frequency_x=2, frequency_y=3))
    np.testing.assert_array_equal(planar.values, repeat.values)
    assert planar.metadata.source_type == "wave_interference"
    assert radial.values.min() >= 0 and radial.values.max() <= 1


def test_mandelbrot_field_is_bounded_and_changes_with_view() -> None:
    standard = generate_mandelbrot_field((24, 32), MandelbrotParameters(iterations=40))
    zoomed = generate_mandelbrot_field((24, 32), MandelbrotParameters(iterations=40, zoom=4))
    assert standard.metadata.source_type == "mandelbrot"
    assert standard.values.min() >= 0 and standard.values.max() <= 1
    assert not np.array_equal(standard.values, zoomed.values)


def test_generator_parameters_reject_invalid_ranges() -> None:
    with pytest.raises(ValueError, match="octaves"):
        generate_fractal_noise((4, 4), NoiseParameters(octaves=0))
    with pytest.raises(ValueError, match="mode"):
        generate_wave_field((4, 4), WaveParameters(mode="spiral"))
    with pytest.raises(ValueError, match="iterations"):
        generate_mandelbrot_field((4, 4), MandelbrotParameters(iterations=0))


def test_long_generator_honors_cancellation() -> None:
    with pytest.raises(WorkerCancelled):
        generate_mandelbrot_field((32, 32), MandelbrotParameters(iterations=20), cancel_check=lambda: True)


def test_generator_reference_statistics_are_stable_with_tolerance() -> None:
    noise = generate_fractal_noise((17, 23), NoiseParameters(seed=42, base_frequency=2, octaves=4, persistence=0.55, lacunarity=2))
    waves = generate_wave_field((17, 23), WaveParameters(frequency_x=2, frequency_y=3))
    mandelbrot = generate_mandelbrot_field((17, 23), MandelbrotParameters(iterations=32))
    assert noise.values.mean() == pytest.approx(0.59642726, abs=2e-5)
    assert noise.values[8, 11] == pytest.approx(0.4119535, abs=2e-5)
    assert waves.values.mean() == pytest.approx(0.5, abs=2e-5)
    assert mandelbrot.values.mean() == pytest.approx(0.3382556, abs=2e-5)


def test_pattern_sources_are_bounded_and_reproducible() -> None:
    sources = [
        generate_voronoi_field((20, 24), VoronoiParameters(seed=4)),
        generate_ridged_noise((20, 24), RidgedNoiseParameters(seed=4)),
        generate_warped_noise((20, 24), WarpedNoiseParameters(seed=4)),
        generate_sdf_field((20, 24), SdfParameters(shape="circle", repeats_x=2, repeats_y=2)),
    ]
    for source in sources:
        assert source.values.dtype == np.float32
        assert np.isfinite(source.values).all()
        assert 0.0 <= float(source.values.min()) <= float(source.values.max()) <= 1.0


def test_p2_and_p3_pattern_sources_are_bounded() -> None:
    sources = [
        generate_chladni_field((16, 20), ChladniParameters()),
        generate_spectral_field((16, 20), SpectralParameters(seed=3, components=4)),
        generate_reaction_diffusion_field((16, 20), ReactionDiffusionParameters(iterations=4)),
        generate_phyllotaxis_field((16, 20), PhyllotaxisParameters(count=40)),
        generate_cellular_automata_field((16, 20), CellularAutomataParameters(iterations=3)),
    ]
    for source in sources:
        assert np.isfinite(source.values).all()
        assert 0.0 <= float(source.values.min()) <= float(source.values.max()) <= 1.0


def test_sdf_boolean_operations_are_bounded() -> None:
    for operation in ("union", "difference", "intersection"):
        source = generate_sdf_field((24, 24), SdfParameters(boolean_shape="circle", boolean_operation=operation, boolean_offset_x=0.2))
        assert np.isfinite(source.values).all()
        assert 0.0 <= float(source.values.min()) <= float(source.values.max()) <= 1.0


def test_p4_flow_erosion_and_contour_sources_are_bounded() -> None:
    flow = generate_flow_field((16, 20), FlowFieldParameters(radial=True))
    erosion = generate_eroded_field((16, 20), ErosionParameters(iterations=3))
    contours = apply_contours(flow, ContourParameters(bands=8))
    for source in (flow, erosion, contours):
        assert np.isfinite(source.values).all()
        assert 0.0 <= float(source.values.min()) <= float(source.values.max()) <= 1.0


def test_branching_and_crack_sources_are_bounded_and_cancelable() -> None:
    branching = generate_lsystem_field((24, 24), LSystemParameters(seed=2, iterations=3))
    cracks = generate_crack_field((24, 24), CrackParameters(seed=2, cracks=4, steps=20))
    assert branching.values.max() <= 1 and cracks.values.max() <= 1
    with pytest.raises(WorkerCancelled):
        generate_crack_field((24, 24), CrackParameters(), cancel_check=lambda: True)


def test_tileable_noise_matches_opposite_boundaries() -> None:
    field = generate_fractal_noise((33, 33), NoiseParameters(base_frequency=3, tileable=True))
    np.testing.assert_allclose(field.values[0, :], field.values[-1, :], atol=1e-6)
    np.testing.assert_allclose(field.values[:, 0], field.values[:, -1], atol=1e-6)


def test_tileable_noise_rejects_non_integer_octave_frequency() -> None:
    with pytest.raises(ValueError, match="integer frequency"):
        generate_fractal_noise((16, 16), NoiseParameters(base_frequency=1.5, tileable=True))


def test_normalized_field_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        NormalizedField(np.array([[0.0, np.nan], [0.0, 1.0]], dtype=np.float32), FieldMetadata("x", "y"))
    with pytest.raises(ValueError, match="between 0 and 1"):
        NormalizedField(np.array([[0.0, 2.0], [0.0, 1.0]], dtype=np.float32), FieldMetadata("x", "y"))


def test_procedural_field_reaches_existing_validated_mesh_path() -> None:
    field = generate_fractal_noise((16, 16), NoiseParameters(seed=7))
    physical = field.values * 5.0
    mesh = generate_solid_mesh(physical, 100.0, 100.0, 3.0)
    report = validate_mesh(mesh)
    assert report.valid
    assert report.bounds_mm == ((-50.0, 50.0), (-3.0, 5.0), (-50.0, 50.0))
