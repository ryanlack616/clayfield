"""Pure NumPy deterministic procedural field generators."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import cv2
import numpy as np

from clayfield.core.cancellation import check_cancelled
from clayfield.field.model import FieldMetadata, NormalizedField
from clayfield.resource_budget import DEFAULT_BUDGET, ResourceBudget, WorkloadEstimate


@dataclass(frozen=True)
class NoiseParameters:
    """Parameters for deterministic value-noise fractal synthesis."""

    seed: int = 0
    base_frequency: float = 2.0
    octaves: int = 6
    persistence: float = 0.5
    lacunarity: float = 2.0
    amplitude: float = 1.0
    normalization: str = "auto"
    tileable: bool = False

    def validate(self) -> None:
        numbers = (self.base_frequency, self.persistence, self.lacunarity, self.amplitude)
        if not np.isfinite(numbers).all():
            raise ValueError("Noise parameters must be finite")
        if self.base_frequency <= 0 or self.lacunarity <= 0:
            raise ValueError("Noise frequencies must be positive")
        if isinstance(self.octaves, bool) or not isinstance(self.octaves, int) or not 1 <= self.octaves <= 12:
            raise ValueError("Noise octaves must be between 1 and 12")
        if not 0 <= self.persistence <= 1:
            raise ValueError("Noise persistence must be between 0 and 1")
        if not 0 <= self.amplitude <= 1:
            raise ValueError("Noise amplitude must be between 0 and 1")
        if self.normalization not in {"auto", "fixed"}:
            raise ValueError("Noise normalization must be auto or fixed")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("Noise seed must be an integer")
        if self.tileable and any(
            abs(self.base_frequency * self.lacunarity**octave - round(self.base_frequency * self.lacunarity**octave))
            > 1e-6
            for octave in range(self.octaves)
        ):
            raise ValueError("Tileable noise requires integer frequency at every octave")


@dataclass(frozen=True)
class WaveParameters:
    """Parameters for planar or radial wave interference."""

    mode: str = "planar"
    frequency_x: float = 3.0
    frequency_y: float = 3.0
    amplitude_x: float = 1.0
    amplitude_y: float = 1.0
    phase_x: float = 0.0
    phase_y: float = 0.0
    radial_frequency: float = 6.0
    radial_phase: float = 0.0
    center_x: float = 0.5
    center_y: float = 0.5
    output_amplitude: float = 1.0
    normalization: str = "auto"

    def validate(self) -> None:
        numbers = (
            self.frequency_x,
            self.frequency_y,
            self.amplitude_x,
            self.amplitude_y,
            self.phase_x,
            self.phase_y,
            self.radial_frequency,
            self.radial_phase,
            self.center_x,
            self.center_y,
            self.output_amplitude,
        )
        if not np.isfinite(numbers).all():
            raise ValueError("Wave parameters must be finite")
        if self.mode not in {"planar", "radial"}:
            raise ValueError("Wave mode must be planar or radial")
        if self.frequency_x <= 0 or self.frequency_y <= 0 or self.radial_frequency <= 0:
            raise ValueError("Wave frequencies must be positive")
        if not 0 <= self.center_x <= 1 or not 0 <= self.center_y <= 1:
            raise ValueError("Wave center must be between 0 and 1")
        if not 0 <= self.output_amplitude <= 1:
            raise ValueError("Wave output amplitude must be between 0 and 1")
        if self.normalization not in {"auto", "fixed"}:
            raise ValueError("Wave normalization must be auto or fixed")


@dataclass(frozen=True)
class MandelbrotParameters:
    """Parameters for a smooth escape-time Mandelbrot field."""

    center_real: float = -0.5
    center_imaginary: float = 0.0
    zoom: float = 1.0
    iterations: int = 100
    escape_radius: float = 2.0
    exponent: int = 2
    contrast: float = 1.0
    invert: bool = False

    def validate(self) -> None:
        numbers = (self.center_real, self.center_imaginary, self.zoom, self.escape_radius, self.contrast)
        if not np.isfinite(numbers).all():
            raise ValueError("Mandelbrot parameters must be finite")
        if self.zoom <= 0 or self.escape_radius <= 1 or self.contrast <= 0:
            raise ValueError("Mandelbrot zoom, escape radius, and contrast must be positive")
        if (
            isinstance(self.iterations, bool)
            or not isinstance(self.iterations, int)
            or not 1 <= self.iterations <= 2000
        ):
            raise ValueError("Mandelbrot iterations must be between 1 and 2000")
        if isinstance(self.exponent, bool) or not isinstance(self.exponent, int) or not 2 <= self.exponent <= 8:
            raise ValueError("Mandelbrot exponent must be between 2 and 8")


@dataclass(frozen=True)
class VoronoiParameters:
    seed: int = 0
    cell_density: float = 8.0
    jitter: float = 1.0
    mode: str = "boundary"
    edge_width: float = 0.15
    normalization: str = "auto"

    def validate(self) -> None:
        if (
            not np.isfinite([self.cell_density, self.jitter, self.edge_width]).all()
            or self.cell_density <= 0
            or not 0 <= self.jitter <= 1
            or self.edge_width <= 0
        ):
            raise ValueError("Voronoi parameters are invalid")
        if self.cell_density > 4096:
            # Each cell is one lattice point; 4096^2 already means 16.7 million
            # cells, which is far beyond any legitimate interactive field. The
            # element-work bound in _generator_workload is the real rejection
            # point; this bound keeps the parameter itself plausible.
            raise ValueError("Voronoi cell density must be at most 4096")
        if self.mode not in {"distance", "boundary", "cells"} or self.normalization not in {"auto", "fixed"}:
            raise ValueError("Voronoi mode or normalization is invalid")


@dataclass(frozen=True)
class RidgedNoiseParameters:
    seed: int = 0
    base_frequency: float = 2.0
    octaves: int = 6
    persistence: float = 0.5
    lacunarity: float = 2.0
    sharpness: float = 2.0

    def validate(self) -> None:
        NoiseParameters(self.seed, self.base_frequency, self.octaves, self.persistence, self.lacunarity).validate()
        if not np.isfinite(self.sharpness) or self.sharpness <= 0:
            raise ValueError("Ridged noise sharpness must be positive")


@dataclass(frozen=True)
class WarpedNoiseParameters:
    seed: int = 0
    base_frequency: float = 2.0
    warp_frequency: float = 2.0
    warp_strength: float = 0.25
    octaves: int = 5
    persistence: float = 0.5
    lacunarity: float = 2.0

    def validate(self) -> None:
        NoiseParameters(self.seed, self.base_frequency, self.octaves, self.persistence, self.lacunarity).validate()
        if (
            not np.isfinite([self.warp_frequency, self.warp_strength]).all()
            or self.warp_frequency <= 0
            or self.warp_strength < 0
        ):
            raise ValueError("Warped noise parameters are invalid")


@dataclass(frozen=True)
class SdfParameters:
    shape: str = "circle"
    radius: float = 0.35
    width: float = 0.6
    height: float = 0.6
    repeats_x: int = 1
    repeats_y: int = 1
    edge_softness: float = 0.05
    invert: bool = False
    boolean_shape: str = "none"
    boolean_operation: str = "union"
    boolean_offset_x: float = 0.0
    boolean_offset_y: float = 0.0

    def validate(self) -> None:
        if (
            self.shape not in {"circle", "rectangle"}
            or self.boolean_shape not in {"none", "circle", "rectangle"}
            or self.boolean_operation not in {"union", "difference", "intersection"}
            or not np.isfinite(
                [self.radius, self.width, self.height, self.edge_softness, self.boolean_offset_x, self.boolean_offset_y]
            ).all()
        ):
            raise ValueError("SDF shape parameters are invalid")
        if self.radius <= 0 or self.width <= 0 or self.height <= 0 or self.edge_softness <= 0:
            raise ValueError("SDF dimensions must be positive")
        if (
            isinstance(self.repeats_x, bool)
            or isinstance(self.repeats_y, bool)
            or not 1 <= self.repeats_x <= 64
            or not 1 <= self.repeats_y <= 64
        ):
            raise ValueError("SDF repeats must be between 1 and 64")


@dataclass(frozen=True)
class ChladniParameters:
    mode_x: int = 3
    mode_y: int = 5
    phase: float = 0.0
    threshold: float = 0.0
    line_width: float = 0.2

    def validate(self) -> None:
        if (
            isinstance(self.mode_x, bool)
            or isinstance(self.mode_y, bool)
            or not 1 <= self.mode_x <= 64
            or not 1 <= self.mode_y <= 64
        ):
            raise ValueError("Chladni modes must be between 1 and 64")
        if not np.isfinite([self.phase, self.threshold, self.line_width]).all() or self.line_width <= 0:
            raise ValueError("Chladni parameters are invalid")


@dataclass(frozen=True)
class SpectralParameters:
    seed: int = 0
    components: int = 12
    minimum_frequency: float = 1.0
    maximum_frequency: float = 12.0
    anisotropy: float = 1.0
    amplitude_falloff: float = 1.0

    def validate(self) -> None:
        if isinstance(self.components, bool) or not 1 <= self.components <= 128:
            raise ValueError("Spectral components must be between 1 and 128")
        values = (self.minimum_frequency, self.maximum_frequency, self.anisotropy, self.amplitude_falloff)
        if (
            not np.isfinite(values).all()
            or self.minimum_frequency <= 0
            or self.maximum_frequency < self.minimum_frequency
            or self.anisotropy <= 0
            or self.amplitude_falloff < 0
        ):
            raise ValueError("Spectral parameters are invalid")


@dataclass(frozen=True)
class ReactionDiffusionParameters:
    seed: int = 0
    iterations: int = 300
    feed: float = 0.055
    kill: float = 0.062
    diffusion_a: float = 1.0
    diffusion_b: float = 0.5

    def validate(self) -> None:
        if isinstance(self.iterations, bool) or not 1 <= self.iterations <= 5000:
            raise ValueError("Reaction-diffusion iterations must be between 1 and 5000")
        if (
            not np.isfinite([self.feed, self.kill, self.diffusion_a, self.diffusion_b]).all()
            or min(self.feed, self.kill, self.diffusion_a, self.diffusion_b) < 0
        ):
            raise ValueError("Reaction-diffusion parameters are invalid")


@dataclass(frozen=True)
class PhyllotaxisParameters:
    count: int = 500
    divergence_degrees: float = 137.50776
    growth: float = 0.018
    point_radius: float = 0.025
    invert: bool = False

    def validate(self) -> None:
        if isinstance(self.count, bool) or not 1 <= self.count <= 10000:
            raise ValueError("Phyllotaxis count must be between 1 and 10000")
        if (
            not np.isfinite([self.divergence_degrees, self.growth, self.point_radius]).all()
            or self.growth <= 0
            or self.point_radius <= 0
        ):
            raise ValueError("Phyllotaxis parameters are invalid")


@dataclass(frozen=True)
class CellularAutomataParameters:
    seed: int = 0
    iterations: int = 10
    initial_density: float = 0.45
    birth_limit: int = 4
    survival_limit: int = 4

    def validate(self) -> None:
        if isinstance(self.iterations, bool) or not 1 <= self.iterations <= 100:
            raise ValueError("Cellular automata iterations must be between 1 and 100")
        if not 0 <= self.initial_density <= 1 or not 0 <= self.birth_limit <= 8 or not 0 <= self.survival_limit <= 8:
            raise ValueError("Cellular automata parameters are invalid")


@dataclass(frozen=True)
class FlowFieldParameters:
    frequency: float = 4.0
    swirl: float = 1.0
    radial: bool = False
    bands: int = 8

    def validate(self) -> None:
        if not np.isfinite([self.frequency, self.swirl]).all() or self.frequency <= 0 or self.swirl < 0:
            raise ValueError("Flow-field parameters are invalid")
        if isinstance(self.bands, bool) or not 1 <= self.bands <= 128:
            raise ValueError("Flow-field bands must be between 1 and 128")


@dataclass(frozen=True)
class ErosionParameters:
    seed: int = 0
    iterations: int = 50
    strength: float = 0.25
    evaporation: float = 0.1

    def validate(self) -> None:
        if isinstance(self.iterations, bool) or not 1 <= self.iterations <= 500:
            raise ValueError("Erosion iterations must be between 1 and 500")
        if (
            not np.isfinite([self.strength, self.evaporation]).all()
            or not 0 <= self.strength <= 1
            or not 0 <= self.evaporation <= 1
        ):
            raise ValueError("Erosion parameters are invalid")


@dataclass(frozen=True)
class LSystemParameters:
    seed: int = 0
    iterations: int = 4
    branch_angle_degrees: float = 25.0
    length: float = 0.18
    length_reduction: float = 0.7
    thickness: float = 0.025
    branch_probability: float = 0.85

    def validate(self) -> None:
        values = (
            self.branch_angle_degrees,
            self.length,
            self.length_reduction,
            self.thickness,
            self.branch_probability,
        )
        if isinstance(self.iterations, bool) or not 1 <= self.iterations <= 8 or not np.isfinite(values).all():
            raise ValueError("L-system parameters are invalid")
        if (
            self.length <= 0
            or not 0 < self.length_reduction < 1
            or self.thickness <= 0
            or not 0 <= self.branch_probability <= 1
        ):
            raise ValueError("L-system parameters are invalid")


@dataclass(frozen=True)
class CrackParameters:
    seed: int = 0
    cracks: int = 12
    steps: int = 80
    step_length: float = 0.02
    branch_probability: float = 0.08
    thickness: float = 0.01

    def validate(self) -> None:
        values = (self.step_length, self.branch_probability, self.thickness)
        if (
            isinstance(self.cracks, bool)
            or isinstance(self.steps, bool)
            or not 1 <= self.cracks <= 512
            or not 1 <= self.steps <= 2000
            or not np.isfinite(values).all()
        ):
            raise ValueError("Crack parameters are invalid")
        if self.step_length <= 0 or not 0 <= self.branch_probability <= 1 or self.thickness <= 0:
            raise ValueError("Crack parameters are invalid")


@dataclass(frozen=True)
class TilingParameters:
    seed: int = 0
    scale: float = 8.0
    line_width: float = 0.18
    rotation: float = 0.0

    def validate(self) -> None:
        if (
            not np.isfinite([self.scale, self.line_width, self.rotation]).all()
            or self.scale <= 0
            or not 0 < self.line_width <= 1
        ):
            raise ValueError("Tiling parameters are invalid")


@dataclass(frozen=True)
class SuperformulaParameters:
    m: float = 5.0
    n1: float = 0.3
    n2: float = 1.0
    n3: float = 1.0
    scale: float = 0.35
    edge_softness: float = 0.05

    def validate(self) -> None:
        if (
            not np.isfinite([self.m, self.n1, self.n2, self.n3, self.scale, self.edge_softness]).all()
            or min(self.n1, self.n2, self.n3, self.scale, self.edge_softness) <= 0
        ):
            raise ValueError("Superformula parameters are invalid")


@dataclass(frozen=True)
class GaussianPeakParameters:
    seed: int = 0
    count: int = 8
    width: float = 0.12
    height: float = 1.0
    crater: bool = False

    def validate(self) -> None:
        if (
            isinstance(self.count, bool)
            or not 1 <= self.count <= 256
            or not np.isfinite([self.width, self.height]).all()
            or self.width <= 0
            or self.height <= 0
        ):
            raise ValueError("Gaussian peak parameters are invalid")


@dataclass(frozen=True)
class JuliaParameters:
    center_real: float = 0.0
    center_imaginary: float = 0.0
    constant_real: float = -0.7
    constant_imaginary: float = 0.27015
    zoom: float = 1.0
    iterations: int = 100
    contrast: float = 1.0
    invert: bool = False

    def validate(self) -> None:
        values = (
            self.center_real,
            self.center_imaginary,
            self.constant_real,
            self.constant_imaginary,
            self.zoom,
            self.contrast,
        )
        if not np.isfinite(values).all() or self.zoom <= 0 or self.contrast <= 0:
            raise ValueError("Julia parameters are invalid")
        if isinstance(self.iterations, bool) or not 1 <= self.iterations <= 2000:
            raise ValueError("Julia iterations must be between 1 and 2000")


@dataclass(frozen=True)
class MoireParameters:
    frequency_a: float = 8.0
    frequency_b: float = 8.5
    angle_a: float = 0.0
    angle_b: float = 0.35
    phase_a: float = 0.0
    phase_b: float = 0.0
    radial: bool = False

    def validate(self) -> None:
        if (
            not np.isfinite(
                [self.frequency_a, self.frequency_b, self.angle_a, self.angle_b, self.phase_a, self.phase_b]
            ).all()
            or self.frequency_a <= 0
            or self.frequency_b <= 0
        ):
            raise ValueError("Moire parameters are invalid")


@dataclass(frozen=True)
class GaborParameters:
    seed: int = 0
    frequency: float = 12.0
    orientation: float = 0.0
    sigma: float = 0.08
    components: int = 4

    def validate(self) -> None:
        if (
            isinstance(self.components, bool)
            or not 1 <= self.components <= 32
            or not np.isfinite([self.frequency, self.orientation, self.sigma]).all()
            or self.frequency <= 0
            or self.sigma <= 0
        ):
            raise ValueError("Gabor parameters are invalid")


def _generator_workload(
    shape: tuple[int, int],
    parameters,
    *,
    budget: ResourceBudget = DEFAULT_BUDGET,
) -> WorkloadEstimate | None:
    """Estimate memory and element-work for one procedural generator.

    This is a *work* budget, not a fabrication-resolution cap. It rejects
    allocations that cannot fit the configured CPU budget, warns when the
    element-operation count is large enough to be felt interactively
    (``work_soft_units``), and rejects element-operation counts that cannot
    finish in any plausible interactive session (``work_hard_units``). Every
    built-in generator has a cost model, so the estimate is normally not
    ``None``; the optional return keeps third-party parameter classes from
    failing the call.
    """
    if len(shape) != 2:
        raise ValueError("Generator shape must contain two dimensions")
    rows, columns = shape
    if isinstance(rows, bool) or isinstance(columns, bool) or not isinstance(rows, int) or not isinstance(columns, int):
        raise ValueError("Generator dimensions must be integers")
    if rows < 2 or columns < 2:
        raise ValueError("Generator requires at least 2x2 samples")
    if max(rows, columns) > budget.max_dimension:
        raise ValueError(
            f"Generator resolution {rows} x {columns} exceeds the absolute "
            f"allocation limit of {budget.max_dimension} per axis"
        )
    pixels = rows * columns
    kind = type(parameters).__name__
    work = 0
    memory = 0
    if isinstance(parameters, VoronoiParameters):
        cells = max(1, int(round(parameters.cell_density)))
        point_bytes = cells * cells * 2 * 4
        work = cells * cells * pixels * 4
        memory = pixels * 4 * 4 + point_bytes
    elif isinstance(parameters, ReactionDiffusionParameters):
        work = parameters.iterations * pixels * 4
        memory = pixels * 4 * 4
    elif isinstance(parameters, PhyllotaxisParameters):
        work = parameters.count * pixels * 2
        memory = pixels * 4 * 3
    elif isinstance(parameters, CellularAutomataParameters):
        work = parameters.iterations * pixels * 2
        memory = pixels * 4 * 2
    elif isinstance(parameters, ErosionParameters):
        work = parameters.iterations * pixels * 4
        memory = pixels * 4 * 4
    elif isinstance(parameters, MandelbrotParameters):
        work = parameters.iterations * pixels * 4
        memory = pixels * 4 * 6
    elif isinstance(parameters, JuliaParameters):
        work = parameters.iterations * pixels * 4
        memory = pixels * 4 * 6
    elif isinstance(parameters, GaborParameters):
        work = parameters.components * pixels * 2
        memory = pixels * 4 * 3
    elif isinstance(parameters, GaussianPeakParameters):
        work = parameters.count * pixels * 2
        memory = pixels * 4 * 2
    elif isinstance(parameters, SpectralParameters):
        work = parameters.components * pixels * 2
        memory = pixels * 4 * 3
    elif isinstance(parameters, NoiseParameters):
        work = parameters.octaves * pixels * 2
        memory = pixels * 4 * 3
    elif isinstance(parameters, (RidgedNoiseParameters, WarpedNoiseParameters)):
        work = parameters.octaves * pixels * 2
        memory = pixels * 4 * 3
    elif isinstance(parameters, CrackParameters):
        work = parameters.cracks * parameters.steps * 2
        memory = pixels * 4 * 2
    elif isinstance(parameters, WaveParameters):
        work = pixels * 6
        memory = pixels * 4 * 2
    elif isinstance(parameters, SdfParameters):
        # Two distance evaluations per sample when a boolean shape is active,
        # one otherwise. Meshgrid coordinates add two more full planes.
        work = pixels * (12 if parameters.boolean_shape != "none" else 8)
        memory = pixels * 4 * 4
    elif isinstance(parameters, ChladniParameters):
        work = pixels * 4
        memory = pixels * 4 * 2
    elif isinstance(parameters, FlowFieldParameters):
        work = pixels * 6
        memory = pixels * 4 * 2
    elif isinstance(parameters, LSystemParameters):
        # The frontier doubles at most once per depth level. Rasterization cost
        # is dominated by the per-pixel canvas conversion, not the segment count.
        segments = min(2**parameters.iterations, 256)
        work = segments * 4 + pixels * 2
        memory = pixels * 2
    elif isinstance(parameters, TilingParameters):
        # Penrose and Truchet are both per-pixel interference/tile evaluations.
        work = pixels * 6
        memory = pixels * 4 * 2
    elif isinstance(parameters, SuperformulaParameters):
        work = pixels * 8
        memory = pixels * 4 * 2
    elif isinstance(parameters, MoireParameters):
        work = pixels * 6
        memory = pixels * 4 * 2
    else:
        return None
    estimate = WorkloadEstimate(
        persistent_bytes=memory,
        temporary_cpu_bytes=0,
        work_units=work,
        confidence="formula",
        breakdown={"pixels": pixels, "generator_bytes": memory},
    )
    if estimate.total_cpu_bytes > budget.cpu_limit_bytes:
        raise ValueError(
            f"{kind} at {rows} x {columns} requires approximately "
            f"{estimate.total_cpu_mebibytes:.0f} MiB; the configured CPU budget is "
            f"{budget.cpu_limit_bytes / (1024 * 1024):.0f} MiB"
        )
    if work > budget.work_hard_units:
        raise ValueError(
            f"{kind} at {rows} x {columns} performs about {work:,} element "
            f"operations; the hard work limit is {budget.work_hard_units:,}. "
            f"Reduce the resolution or the generator's iteration/density settings."
        )
    if work > budget.work_soft_units:
        warnings.warn(
            f"{kind} at {rows} x {columns} performs about {work:,} element operations; this may be slow interactively",
            RuntimeWarning,
            stacklevel=2,
        )
    return estimate


def _seed_for_octave(seed: int, octave: int) -> np.random.SeedSequence:
    """Create an octave-specific seed without depending on RNG call order."""
    return np.random.SeedSequence([seed % (1 << 64), octave])


def _value_noise(rows: int, columns: int, frequency: float, seed: np.random.SeedSequence, tileable: bool) -> np.ndarray:
    """Sample a bilinearly interpolated random lattice on vertex coordinates."""
    cells_x = max(1, int(np.ceil(frequency)))
    cells_y = max(1, int(np.ceil(frequency)))
    rng = np.random.default_rng(seed)
    lattice = rng.random((cells_y + 1, cells_x + 1), dtype=np.float32) * 2.0 - 1.0
    if tileable:
        lattice[-1, :] = lattice[0, :]
        lattice[:, -1] = lattice[:, 0]

    x = np.linspace(0.0, frequency, columns, dtype=np.float32)
    y = np.linspace(0.0, frequency, rows, dtype=np.float32)
    x_index = np.minimum(x.astype(np.int32), cells_x - 1)
    y_index = np.minimum(y.astype(np.int32), cells_y - 1)
    x_fraction = x - x_index
    y_fraction = y - y_index
    x_fraction = np.minimum(x_fraction, 1.0)
    y_fraction = np.minimum(y_fraction, 1.0)

    top_left = lattice[y_index[:, None], x_index[None, :]]
    top_right = lattice[y_index[:, None], x_index[None, :] + 1]
    bottom_left = lattice[y_index[:, None] + 1, x_index[None, :]]
    bottom_right = lattice[y_index[:, None] + 1, x_index[None, :] + 1]
    horizontal_top = top_left + (top_right - top_left) * x_fraction[None, :]
    horizontal_bottom = bottom_left + (bottom_right - bottom_left) * x_fraction[None, :]
    return horizontal_top + (horizontal_bottom - horizontal_top) * y_fraction[:, None]


def generate_fractal_noise(
    shape: tuple[int, int],
    parameters: NoiseParameters | None = None,
    *,
    cancel_check=None,
) -> NormalizedField:
    """Generate a deterministic normalized fBm-style value-noise field.

    Frequencies are cycles across the normalized field domain. Fields use the
    V2 vertex-lattice convention, so the first and last samples map to the
    physical boundary of the mesh.
    """
    parameters = parameters or NoiseParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    if len(shape) != 2 or any(isinstance(size, bool) or not isinstance(size, int) or size < 2 for size in shape):
        raise ValueError("Noise field shape must contain two dimensions of at least 2")
    rows, columns = shape

    field = np.zeros((rows, columns), dtype=np.float32)
    weight = 1.0
    total_weight = 0.0
    for octave in range(parameters.octaves):
        check_cancelled(cancel_check)
        frequency = parameters.base_frequency * parameters.lacunarity**octave
        field += (
            _value_noise(rows, columns, frequency, _seed_for_octave(parameters.seed, octave), parameters.tileable)
            * weight
        )
        total_weight += weight
        weight *= parameters.persistence
    field /= total_weight
    check_cancelled(cancel_check)

    if parameters.normalization == "auto":
        minimum, maximum = float(field.min()), float(field.max())
        values = (field - minimum) / (maximum - minimum) if maximum > minimum else np.zeros_like(field)
    else:
        values = 0.5 + field * parameters.amplitude * 0.5
        values = np.clip(values, 0.0, 1.0)
    values = np.asarray(values, dtype=np.float32)
    metadata = FieldMetadata(
        source_type="fractal_noise",
        algorithm="value_fbm",
        algorithm_version="1",
        seed=parameters.seed,
        tileable=parameters.tileable,
    )
    return NormalizedField(values, metadata)


def _normalize_signed(
    values: np.ndarray, normalization: str, amplitude: float = 1.0, theoretical_peak: float = 1.0
) -> np.ndarray:
    if normalization == "auto":
        minimum, maximum = float(values.min()), float(values.max())
        return (values - minimum) / (maximum - minimum) if maximum > minimum else np.zeros_like(values)
    relative = np.clip(values / max(theoretical_peak, 1e-6), -1.0, 1.0)
    return np.clip(0.5 + relative * amplitude * 0.5, 0.0, 1.0)


def generate_wave_field(
    shape: tuple[int, int], parameters: WaveParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    """Generate deterministic planar or radial wave interference."""
    parameters = parameters or WaveParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    check_cancelled(cancel_check)
    if len(shape) != 2 or any(isinstance(size, bool) or not isinstance(size, int) or size < 2 for size in shape):
        raise ValueError("Wave field shape must contain two dimensions of at least 2")
    rows, columns = shape
    x = np.linspace(0.0, 1.0, columns, dtype=np.float32)
    y = np.linspace(0.0, 1.0, rows, dtype=np.float32)
    if parameters.mode == "radial":
        distance = np.hypot(x[None, :] - parameters.center_x, y[:, None] - parameters.center_y)
        raw = np.sin(2.0 * np.pi * parameters.radial_frequency * distance + parameters.radial_phase)
        theoretical_peak = 1.0
    else:
        horizontal = parameters.amplitude_x * np.sin(2.0 * np.pi * parameters.frequency_x * x + parameters.phase_x)
        vertical = parameters.amplitude_y * np.sin(2.0 * np.pi * parameters.frequency_y * y + parameters.phase_y)
        raw = horizontal[None, :] + vertical[:, None]
        theoretical_peak = abs(parameters.amplitude_x) + abs(parameters.amplitude_y)
    values = _normalize_signed(raw, parameters.normalization, parameters.output_amplitude, theoretical_peak).astype(
        np.float32
    )
    metadata = FieldMetadata(source_type="wave_interference", algorithm="wave_interference", algorithm_version="1")
    return NormalizedField(values, metadata)


def generate_mandelbrot_field(
    shape: tuple[int, int], parameters: MandelbrotParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    """Generate a smooth Mandelbrot escape-time field."""
    parameters = parameters or MandelbrotParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    if len(shape) != 2 or any(isinstance(size, bool) or not isinstance(size, int) or size < 2 for size in shape):
        raise ValueError("Mandelbrot field shape must contain two dimensions of at least 2")
    rows, columns = shape
    span_x = 3.0 / parameters.zoom
    span_y = span_x * rows / columns
    real = np.linspace(
        parameters.center_real - span_x / 2.0, parameters.center_real + span_x / 2.0, columns, dtype=np.float64
    )
    imaginary = np.linspace(
        parameters.center_imaginary - span_y / 2.0, parameters.center_imaginary + span_y / 2.0, rows, dtype=np.float64
    )
    c = real[None, :] + 1j * imaginary[:, None]
    z = np.zeros_like(c)
    escaped = np.zeros(c.shape, dtype=bool)
    smooth = np.full(c.shape, float(parameters.iterations), dtype=np.float64)
    escape_squared = parameters.escape_radius * parameters.escape_radius
    for iteration in range(parameters.iterations):
        check_cancelled(cancel_check)
        active = ~escaped
        z[active] = z[active] ** parameters.exponent + c[active]
        magnitude_squared = z.real * z.real + z.imag * z.imag
        newly_escaped = active & (magnitude_squared > escape_squared)
        if np.any(newly_escaped):
            magnitude = np.sqrt(magnitude_squared[newly_escaped])
            smooth[newly_escaped] = iteration + 1.0 - np.log(np.log(magnitude)) / np.log(parameters.exponent)
        escaped |= newly_escaped
        if escaped.all():
            break
    check_cancelled(cancel_check)
    values = np.clip(smooth / parameters.iterations, 0.0, 1.0)
    values = np.power(values, 1.0 / parameters.contrast)
    if parameters.invert:
        values = 1.0 - values
    metadata = FieldMetadata(source_type="mandelbrot", algorithm="smooth_escape_time", algorithm_version="1")
    return NormalizedField(values.astype(np.float32), metadata)


def generate_voronoi_field(
    shape: tuple[int, int], parameters: VoronoiParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    """Generate a deterministic cellular Voronoi/Worley field."""
    parameters = parameters or VoronoiParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    if min(shape) < 2:
        raise ValueError("Voronoi field requires at least 2x2 samples")
    rng = np.random.default_rng(parameters.seed % (1 << 64))
    cells = max(1, int(round(parameters.cell_density)))
    points = (np.arange(cells * cells, dtype=np.float32).reshape(cells, cells, 1) / cells) + (
        rng.random((cells, cells, 2), dtype=np.float32) - 0.5
    ) * parameters.jitter / cells
    y, x = np.mgrid[0:rows, 0:columns].astype(np.float32)
    x = x / max(1, columns - 1)
    y = y / max(1, rows - 1)
    nearest = np.full((rows, columns), np.inf, dtype=np.float32)
    second = np.full_like(nearest, np.inf)
    for point in points.reshape(-1, 2):
        check_cancelled(cancel_check)
        distance = np.hypot(x - point[0], y - point[1])
        closer = distance < nearest
        second = np.where(closer, nearest, np.minimum(second, distance))
        nearest = np.minimum(nearest, distance)
    if parameters.mode == "boundary":
        values = np.clip((second - nearest) / parameters.edge_width, 0.0, 1.0)
    elif parameters.mode == "distance":
        values = 1.0 - nearest / max(float(nearest.max()), 1e-6)
    else:
        values = nearest
    if parameters.normalization == "auto":
        minimum, maximum = float(values.min()), float(values.max())
        values = (values - minimum) / (maximum - minimum) if maximum > minimum else np.zeros_like(values)
    else:
        values = np.clip(values, 0.0, 1.0)
    return NormalizedField(values.astype(np.float32), FieldMetadata("voronoi", "voronoi", "1", parameters.seed))


def generate_ridged_noise(
    shape: tuple[int, int], parameters: RidgedNoiseParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    """Generate sharp mountain-like ridges from deterministic fBm noise."""
    parameters = parameters or RidgedNoiseParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    source = generate_fractal_noise(
        shape,
        NoiseParameters(
            parameters.seed,
            parameters.base_frequency,
            parameters.octaves,
            parameters.persistence,
            parameters.lacunarity,
        ),
        cancel_check=cancel_check,
    )
    signed = np.abs(source.values * 2.0 - 1.0)
    values = np.power(1.0 - signed, parameters.sharpness, dtype=np.float32)
    return NormalizedField(values, FieldMetadata("ridged_noise", "ridged_fbm", "1", parameters.seed))


def generate_warped_noise(
    shape: tuple[int, int], parameters: WarpedNoiseParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    """Generate noise with deterministic coordinate warping."""
    parameters = parameters or WarpedNoiseParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    base = generate_fractal_noise(
        shape,
        NoiseParameters(
            parameters.seed,
            parameters.base_frequency,
            parameters.octaves,
            parameters.persistence,
            parameters.lacunarity,
        ),
        cancel_check=cancel_check,
    )
    warp_x = (
        generate_fractal_noise(
            shape,
            NoiseParameters(parameters.seed + 1, parameters.warp_frequency, 2, 0.5, 2.0),
            cancel_check=cancel_check,
        ).values
        * 2.0
        - 1.0
    )
    warp_y = (
        generate_fractal_noise(
            shape,
            NoiseParameters(parameters.seed + 2, parameters.warp_frequency, 2, 0.5, 2.0),
            cancel_check=cancel_check,
        ).values
        * 2.0
        - 1.0
    )
    map_x = (
        np.broadcast_to(np.arange(columns, dtype=np.float32)[None, :], (rows, columns))
        + warp_x * parameters.warp_strength * columns
    )
    map_y = (
        np.broadcast_to(np.arange(rows, dtype=np.float32)[:, None], (rows, columns))
        + warp_y * parameters.warp_strength * rows
    )
    warped = cv2.remap(base.values, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return NormalizedField(
        np.clip(warped, 0.0, 1.0).astype(np.float32),
        FieldMetadata("warped_noise", "domain_warped_fbm", "1", parameters.seed),
    )


def generate_sdf_field(
    shape: tuple[int, int], parameters: SdfParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    """Generate a repeated signed-distance geometric relief field."""
    parameters = parameters or SdfParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    if min(shape) < 2:
        raise ValueError("SDF field requires at least 2x2 samples")
    x = (np.linspace(0.0, 1.0, columns, dtype=np.float32) * parameters.repeats_x) % 1.0 - 0.5
    y = (np.linspace(0.0, 1.0, rows, dtype=np.float32) * parameters.repeats_y) % 1.0 - 0.5
    xx, yy = np.meshgrid(x, y)
    if parameters.shape == "circle":
        distance = np.hypot(xx, yy) - parameters.radius
    else:
        distance = np.maximum(np.abs(xx) - parameters.width / 2.0, np.abs(yy) - parameters.height / 2.0)
    if parameters.boolean_shape != "none":
        shifted_x = xx - parameters.boolean_offset_x
        shifted_y = yy - parameters.boolean_offset_y
        if parameters.boolean_shape == "circle":
            second_distance = np.hypot(shifted_x, shifted_y) - parameters.radius
        else:
            second_distance = np.maximum(
                np.abs(shifted_x) - parameters.width / 2.0, np.abs(shifted_y) - parameters.height / 2.0
            )
        if parameters.boolean_operation == "union":
            distance = np.minimum(distance, second_distance)
        elif parameters.boolean_operation == "difference":
            distance = np.maximum(distance, -second_distance)
        else:
            distance = np.maximum(distance, second_distance)
    values = np.clip(0.5 - distance / parameters.edge_softness, 0.0, 1.0)
    if parameters.invert:
        values = 1.0 - values
    check_cancelled(cancel_check)
    return NormalizedField(values.astype(np.float32), FieldMetadata("sdf", f"sdf_{parameters.shape}", "1"))


def generate_chladni_field(
    shape: tuple[int, int], parameters: ChladniParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    parameters = parameters or ChladniParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    x = np.linspace(0.0, 1.0, columns, dtype=np.float32)
    y = np.linspace(0.0, 1.0, rows, dtype=np.float32)
    raw = np.sin(np.pi * parameters.mode_x * x)[None, :] * np.sin(np.pi * parameters.mode_y * y)[:, None]
    raw += (
        np.sin(np.pi * parameters.mode_y * x + parameters.phase)[None, :]
        * np.sin(np.pi * parameters.mode_x * y)[:, None]
    )
    values = np.exp(-np.abs(raw - parameters.threshold) / parameters.line_width)
    check_cancelled(cancel_check)
    return NormalizedField(values.astype(np.float32), FieldMetadata("chladni", "chladni_modes", "1"))


def generate_spectral_field(
    shape: tuple[int, int], parameters: SpectralParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    parameters = parameters or SpectralParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    x = np.linspace(0.0, 1.0, columns, dtype=np.float32)[None, :]
    y = np.linspace(0.0, 1.0, rows, dtype=np.float32)[:, None]
    rng = np.random.default_rng(parameters.seed % (1 << 64))
    values = np.zeros((rows, columns), dtype=np.float32)
    for index in range(parameters.components):
        check_cancelled(cancel_check)
        frequency = rng.uniform(parameters.minimum_frequency, parameters.maximum_frequency)
        angle = rng.uniform(0.0, 2.0 * np.pi)
        phase = rng.uniform(0.0, 2.0 * np.pi)
        direction_x, direction_y = np.cos(angle), np.sin(angle) * parameters.anisotropy
        values += np.sin(2.0 * np.pi * frequency * (direction_x * x + direction_y * y) + phase) / (
            (index + 1) ** parameters.amplitude_falloff
        )
    minimum, maximum = float(values.min()), float(values.max())
    values = (values - minimum) / (maximum - minimum) if maximum > minimum else np.zeros_like(values)
    return NormalizedField(values.astype(np.float32), FieldMetadata("spectral", "random_fourier", "1", parameters.seed))


def generate_reaction_diffusion_field(
    shape: tuple[int, int], parameters: ReactionDiffusionParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    parameters = parameters or ReactionDiffusionParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    rng = np.random.default_rng(parameters.seed % (1 << 64))
    a = np.ones((rows, columns), dtype=np.float32)
    b = (rng.random((rows, columns), dtype=np.float32) < 0.02).astype(np.float32)
    kernel = np.array([[0.05, 0.2, 0.05], [0.2, -1.0, 0.2], [0.05, 0.2, 0.05]], dtype=np.float32)
    for _ in range(parameters.iterations):
        check_cancelled(cancel_check)
        lap_a = cv2.filter2D(a, -1, kernel, borderType=cv2.BORDER_REFLECT)
        lap_b = cv2.filter2D(b, -1, kernel, borderType=cv2.BORDER_REFLECT)
        reaction = a * b * b
        a = np.clip(a + parameters.diffusion_a * lap_a - reaction + parameters.feed * (1.0 - a), 0.0, 1.0)
        b = np.clip(b + parameters.diffusion_b * lap_b + reaction - (parameters.kill + parameters.feed) * b, 0.0, 1.0)
    return NormalizedField(
        b.astype(np.float32), FieldMetadata("reaction_diffusion", "gray_scott", "1", parameters.seed)
    )


def generate_phyllotaxis_field(
    shape: tuple[int, int], parameters: PhyllotaxisParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    parameters = parameters or PhyllotaxisParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    y, x = np.mgrid[0:rows, 0:columns].astype(np.float32)
    x = (x / max(1, columns - 1) - 0.5) * 2.0
    y = (y / max(1, rows - 1) - 0.5) * 2.0
    field = np.zeros((rows, columns), dtype=np.float32)
    angle = np.deg2rad(parameters.divergence_degrees)
    for index in range(parameters.count):
        if index % 32 == 0:
            check_cancelled(cancel_check)
        radius = parameters.growth * np.sqrt(index)
        center_x, center_y = radius * np.cos(index * angle), radius * np.sin(index * angle)
        field = np.maximum(
            field, np.exp(-((x - center_x) ** 2 + (y - center_y) ** 2) / (2.0 * parameters.point_radius**2))
        )
    if parameters.invert:
        field = 1.0 - field
    return NormalizedField(
        np.clip(field, 0.0, 1.0).astype(np.float32), FieldMetadata("phyllotaxis", "golden_angle", "1")
    )


def generate_cellular_automata_field(
    shape: tuple[int, int], parameters: CellularAutomataParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    parameters = parameters or CellularAutomataParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rng = np.random.default_rng(parameters.seed % (1 << 64))
    field = (rng.random(shape) < parameters.initial_density).astype(np.float32)
    for _ in range(parameters.iterations):
        check_cancelled(cancel_check)
        neighbors = cv2.filter2D(field, -1, np.ones((3, 3), dtype=np.float32), borderType=cv2.BORDER_CONSTANT) - field
        field = np.where(
            (field > 0) & (neighbors >= parameters.survival_limit)
            | (field == 0) & (neighbors >= parameters.birth_limit),
            1.0,
            0.0,
        ).astype(np.float32)
    return NormalizedField(field, FieldMetadata("cellular_automata", "life_neighbors", "1", parameters.seed))


def generate_flow_field(
    shape: tuple[int, int], parameters: FlowFieldParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    """Generate deterministic flowing bands from a scalar vector-like field."""
    parameters = parameters or FlowFieldParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    y, x = np.mgrid[0:rows, 0:columns].astype(np.float32)
    x = x / max(1, columns - 1) - 0.5
    y = y / max(1, rows - 1) - 0.5
    if parameters.radial:
        angle = np.arctan2(y, x) + parameters.swirl * np.hypot(x, y)
        raw = np.sin(parameters.frequency * angle * parameters.bands)
    else:
        raw = np.sin(2.0 * np.pi * parameters.frequency * (x + parameters.swirl * np.sin(2.0 * np.pi * y)))
    values = (raw + 1.0) * 0.5
    check_cancelled(cancel_check)
    return NormalizedField(values.astype(np.float32), FieldMetadata("flow_field", "flow_bands", "1"))


def generate_eroded_field(
    shape: tuple[int, int], parameters: ErosionParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    """Generate a bounded erosion-style field from deterministic terrain noise."""
    parameters = parameters or ErosionParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    field = generate_fractal_noise(
        shape, NoiseParameters(parameters.seed, 3.0, 5, 0.55, 2.0), cancel_check=cancel_check
    ).values.copy()
    for _ in range(parameters.iterations):
        check_cancelled(cancel_check)
        blurred = cv2.GaussianBlur(field, (0, 0), 1.0)
        gradient = field - blurred
        field = np.clip(field - gradient * parameters.strength, 0.0, 1.0)
        field = field * (1.0 - parameters.evaporation) + blurred * parameters.evaporation
    minimum, maximum = float(field.min()), float(field.max())
    values = (field - minimum) / (maximum - minimum) if maximum > minimum else np.zeros_like(field)
    return NormalizedField(values.astype(np.float32), FieldMetadata("erosion", "bounded_erosion", "1", parameters.seed))


def generate_lsystem_field(
    shape: tuple[int, int], parameters: LSystemParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    """Rasterize deterministic branching growth into a normalized field."""
    parameters = parameters or LSystemParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    rng = np.random.default_rng(parameters.seed % (1 << 64))
    canvas = np.zeros((rows, columns), dtype=np.uint8)
    frontier = [((0.5, 0.92), -np.pi / 2.0, parameters.length, 0)]
    while frontier:
        check_cancelled(cancel_check)
        (x, y), angle, length, depth = frontier.pop()
        end = (x + np.cos(angle) * length, y + np.sin(angle) * length)
        cv2.line(
            canvas,
            (int(x * (columns - 1)), int(y * (rows - 1))),
            (int(end[0] * (columns - 1)), int(end[1] * (rows - 1))),
            255,
            max(1, int(parameters.thickness * min(rows, columns))),
        )
        if depth >= parameters.iterations or not (0 <= end[0] <= 1 and 0 <= end[1] <= 1):
            continue
        next_length = length * parameters.length_reduction
        frontier.append((end, angle + np.deg2rad(parameters.branch_angle_degrees), next_length, depth + 1))
        if rng.random() <= parameters.branch_probability:
            frontier.append((end, angle - np.deg2rad(parameters.branch_angle_degrees), next_length, depth + 1))
    return NormalizedField(
        (canvas.astype(np.float32) / 255.0), FieldMetadata("lsystem", "branching_growth", "1", parameters.seed)
    )


def generate_crack_field(
    shape: tuple[int, int], parameters: CrackParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    """Generate deterministic crack-like random walks as a field."""
    parameters = parameters or CrackParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    rng = np.random.default_rng(parameters.seed % (1 << 64))
    canvas = np.zeros((rows, columns), dtype=np.uint8)
    for _ in range(parameters.cracks):
        check_cancelled(cancel_check)
        position = np.array([rng.uniform(0.0, 1.0), rng.uniform(0.0, 1.0)], dtype=np.float32)
        angle = rng.uniform(0.0, 2.0 * np.pi)
        points = []
        for _ in range(parameters.steps):
            points.append(
                (int(np.clip(position[0], 0, 1) * (columns - 1)), int(np.clip(position[1], 0, 1) * (rows - 1)))
            )
            angle += rng.normal(0.0, 0.18)
            position += np.array([np.cos(angle), np.sin(angle)], dtype=np.float32) * parameters.step_length
            if rng.random() < parameters.branch_probability:
                angle += rng.choice([-1.0, 1.0]) * 0.8
            if not np.all((position >= -0.1) & (position <= 1.1)):
                break
        if len(points) > 1:
            cv2.polylines(
                canvas,
                [np.asarray(points, dtype=np.int32)],
                False,
                255,
                max(1, int(parameters.thickness * min(rows, columns))),
            )
    return NormalizedField(
        canvas.astype(np.float32) / 255.0, FieldMetadata("cracks", "random_walk_cracks", "1", parameters.seed)
    )


def generate_penrose_field(
    shape: tuple[int, int], parameters: TilingParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    """Generate a Penrose-style aperiodic interference field."""
    parameters = parameters or TilingParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    y, x = np.mgrid[0:rows, 0:columns].astype(np.float32)
    x = x / max(1, columns - 1) - 0.5
    y = y / max(1, rows - 1) - 0.5
    golden = (1.0 + np.sqrt(5.0)) / 2.0
    raw = np.zeros_like(x)
    for index in range(5):
        angle = parameters.rotation + index * np.pi / 5.0
        projection = x * np.cos(angle) + y * np.sin(angle)
        raw += np.cos(2.0 * np.pi * parameters.scale * projection * golden**index)
    values = (raw / 5.0 + 1.0) * 0.5
    values = np.clip(1.0 - np.abs(values - 0.5) / max(parameters.line_width, 1e-6), 0.0, 1.0)
    check_cancelled(cancel_check)
    return NormalizedField(
        values.astype(np.float32), FieldMetadata("penrose", "golden_interference", "1", parameters.seed)
    )


def generate_truchet_field(
    shape: tuple[int, int], parameters: TilingParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    """Generate a deterministic Truchet-style diagonal tile field."""
    parameters = parameters or TilingParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    y, x = np.mgrid[0:rows, 0:columns].astype(np.float32)
    tx = (x / max(1, columns - 1) * parameters.scale) % 1.0
    ty = (y / max(1, rows - 1) * parameters.scale) % 1.0
    selector = np.sin((x + parameters.seed) * 12.9898 + (y + parameters.seed) * 78.233) > 0
    diagonal_a = np.abs(tx - ty)
    diagonal_b = np.abs(tx + ty - 1.0)
    distance = np.where(selector, diagonal_a, diagonal_b)
    values = np.clip(1.0 - distance / max(parameters.line_width, 1e-6), 0.0, 1.0)
    check_cancelled(cancel_check)
    return NormalizedField(values.astype(np.float32), FieldMetadata("truchet", "diagonal_tiles", "1", parameters.seed))


def generate_superformula_field(
    shape: tuple[int, int], parameters: SuperformulaParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    parameters = parameters or SuperformulaParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    y, x = np.mgrid[0:rows, 0:columns].astype(np.float32)
    x = x / max(1, columns - 1) - 0.5
    y = y / max(1, rows - 1) - 0.5
    theta = np.arctan2(y, x)
    radial = (
        np.abs(np.cos(parameters.m * theta / 4.0) / 1.0) ** parameters.n2
        + np.abs(np.sin(parameters.m * theta / 4.0) / 1.0) ** parameters.n3
    ) ** (-1.0 / parameters.n1)
    distance = np.hypot(x, y) - radial * parameters.scale
    values = np.clip(0.5 - distance / parameters.edge_softness, 0.0, 1.0)
    check_cancelled(cancel_check)
    return NormalizedField(values.astype(np.float32), FieldMetadata("superformula", "superformula", "1"))


def generate_gaussian_peaks_field(
    shape: tuple[int, int], parameters: GaussianPeakParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    parameters = parameters or GaussianPeakParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    y, x = np.mgrid[0:rows, 0:columns].astype(np.float32)
    x = x / max(1, columns - 1)
    y = y / max(1, rows - 1)
    rng = np.random.default_rng(parameters.seed % (1 << 64))
    values = np.zeros((rows, columns), dtype=np.float32)
    for _ in range(parameters.count):
        check_cancelled(cancel_check)
        cx, cy = rng.random(2)
        peak = np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2.0 * parameters.width**2)) * parameters.height
        values = values - peak if parameters.crater else values + peak
    minimum, maximum = float(values.min()), float(values.max())
    values = (values - minimum) / (maximum - minimum) if maximum > minimum else np.zeros_like(values)
    return NormalizedField(
        values.astype(np.float32), FieldMetadata("gaussian_peaks", "gaussian_clusters", "1", parameters.seed)
    )


def generate_julia_field(
    shape: tuple[int, int], parameters: JuliaParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    parameters = parameters or JuliaParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    span_x = 3.0 / parameters.zoom
    span_y = span_x * rows / columns
    real = np.linspace(parameters.center_real - span_x / 2, parameters.center_real + span_x / 2, columns)
    imaginary = np.linspace(parameters.center_imaginary - span_y / 2, parameters.center_imaginary + span_y / 2, rows)
    z = real[None, :] + 1j * imaginary[:, None]
    c = complex(parameters.constant_real, parameters.constant_imaginary)
    escaped = np.zeros(z.shape, dtype=bool)
    values = np.full(z.shape, float(parameters.iterations), dtype=np.float64)
    for iteration in range(parameters.iterations):
        check_cancelled(cancel_check)
        active = ~escaped
        z[active] = z[active] * z[active] + c
        magnitude = np.abs(z)
        newly = active & (magnitude > 2.0)
        values[newly] = iteration + 1.0 - np.log(np.log(magnitude[newly])) / np.log(2.0)
        escaped |= newly
        if escaped.all():
            break
    result = np.clip(values / parameters.iterations, 0.0, 1.0) ** (1.0 / parameters.contrast)
    if parameters.invert:
        result = 1.0 - result
    return NormalizedField(result.astype(np.float32), FieldMetadata("julia", "julia_escape_time", "1"))


def generate_moire_field(
    shape: tuple[int, int], parameters: MoireParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    parameters = parameters or MoireParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    y, x = np.mgrid[0:rows, 0:columns].astype(np.float32)
    x = x / max(1, columns - 1) - 0.5
    y = y / max(1, rows - 1) - 0.5
    if parameters.radial:
        a = np.hypot(x, y) * parameters.frequency_a + parameters.phase_a
        b = np.hypot(x, y) * parameters.frequency_b + parameters.phase_b
    else:
        a = (
            x * np.cos(parameters.angle_a) + y * np.sin(parameters.angle_a)
        ) * parameters.frequency_a + parameters.phase_a
        b = (
            x * np.cos(parameters.angle_b) + y * np.sin(parameters.angle_b)
        ) * parameters.frequency_b + parameters.phase_b
    values = (np.sin(2.0 * np.pi * a) + np.sin(2.0 * np.pi * b) + 2.0) * 0.25
    check_cancelled(cancel_check)
    return NormalizedField(values.astype(np.float32), FieldMetadata("moire", "dual_interference", "1"))


def generate_gabor_field(
    shape: tuple[int, int], parameters: GaborParameters | None = None, *, cancel_check=None
) -> NormalizedField:
    parameters = parameters or GaborParameters()
    parameters.validate()
    _generator_workload(shape, parameters)
    rows, columns = shape
    y, x = np.mgrid[0:rows, 0:columns].astype(np.float32)
    x = x / max(1, columns - 1) - 0.5
    y = y / max(1, rows - 1) - 0.5
    rng = np.random.default_rng(parameters.seed % (1 << 64))
    values = np.zeros((rows, columns), dtype=np.float32)
    for _ in range(parameters.components):
        check_cancelled(cancel_check)
        angle = parameters.orientation + rng.normal(0.0, 0.25)
        phase = rng.uniform(0.0, 2.0 * np.pi)
        u = x * np.cos(angle) + y * np.sin(angle)
        v = -x * np.sin(angle) + y * np.cos(angle)
        values += np.exp(-(u * u + v * v) / (2.0 * parameters.sigma**2)) * np.cos(
            2.0 * np.pi * parameters.frequency * u + phase
        )
    minimum, maximum = float(values.min()), float(values.max())
    values = (values - minimum) / (maximum - minimum) if maximum > minimum else np.zeros_like(values)
    return NormalizedField(values.astype(np.float32), FieldMetadata("gabor", "gabor_bank", "1", parameters.seed))
