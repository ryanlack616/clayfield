"""CPU-authoritative physical heightfield generation."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from clayfield.image.curves import apply_curve


@dataclass(frozen=True)
class PhysicalDimensions:
    """Physical terrain dimensions in millimeters."""

    width_mm: float = 100.0
    depth_mm: float = 100.0
    minimum_height_mm: float = 0.0
    maximum_height_mm: float = 8.0

    def validate(self) -> None:
        if not np.isfinite([self.width_mm, self.depth_mm, self.minimum_height_mm, self.maximum_height_mm]).all():
            raise ValueError("Terrain dimensions must be finite")
        if self.width_mm <= 0 or self.depth_mm <= 0:
            raise ValueError("Terrain width and depth must be positive")
        if self.minimum_height_mm > self.maximum_height_mm:
            raise ValueError("Minimum height cannot exceed maximum height")


@dataclass(frozen=True)
class HeightOptions:
    """Independent height mapping and modifier controls."""

    normalize: bool = False
    offset_mm: float = 0.0
    scale: float = 1.0
    clamp_min: float = 0.0
    clamp_max: float = 1.0
    smoothing_strength: float = 1.0
    edge_strength: float = 1.0
    noise_octaves: int = 1
    noise_persistence: float = 0.5

    def validate(self) -> None:
        numbers = (
            self.offset_mm,
            self.scale,
            self.clamp_min,
            self.clamp_max,
            self.smoothing_strength,
            self.edge_strength,
            self.noise_persistence,
        )
        if not np.isfinite(numbers).all():
            raise ValueError("Height options must be finite")
        if self.scale <= 0 or not 0 <= self.clamp_min <= self.clamp_max <= 1:
            raise ValueError("Height scale and clamp range are invalid")
        if not 0 <= self.smoothing_strength <= 1 or not 0 <= self.edge_strength <= 1:
            raise ValueError("Modifier strengths must be between 0 and 1")
        if (
            isinstance(self.noise_octaves, bool)
            or not isinstance(self.noise_octaves, int)
            or not 1 <= self.noise_octaves <= 8
        ):
            raise ValueError("Noise octaves must be between 1 and 8")
        if not 0 <= self.noise_persistence <= 1:
            raise ValueError("Noise persistence must be between 0 and 1")


def options_from_state(state) -> HeightOptions:
    return HeightOptions(
        state.height_normalize,
        state.height_offset_mm,
        state.height_scale,
        state.height_clamp_min,
        state.height_clamp_max,
        state.smoothing_strength,
        state.edge_falloff_strength,
        state.noise_octaves,
        state.noise_persistence,
    )


def physical_height_bounds(dimensions: PhysicalDimensions, options: HeightOptions) -> tuple[float, float]:
    span = dimensions.maximum_height_mm - dimensions.minimum_height_mm
    return (
        (dimensions.minimum_height_mm + span * options.clamp_min) * options.scale + options.offset_mm,
        (dimensions.minimum_height_mm + span * options.clamp_max) * options.scale + options.offset_mm,
    )


def resize_heightfield(image: np.ndarray, width: int, height: int) -> np.ndarray:
    """Resize normalized image data with area filtering for downsampling."""
    values = np.asarray(image, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError(f"Heightfield input must be 2D; got {values.shape}")
    if width < 2 or height < 2:
        raise ValueError("Heightfield resolution must be at least 2 by 2")
    interpolation = cv2.INTER_AREA if width <= values.shape[1] and height <= values.shape[0] else cv2.INTER_LINEAR
    return np.clip(cv2.resize(values, (width, height), interpolation=interpolation), 0.0, 1.0).astype(np.float32)


def generate_physical_heightfield(
    image: np.ndarray,
    dimensions: PhysicalDimensions,
    resolution: tuple[int, int] | None = None,
    inverted: bool = False,
    smoothing_sigma: float = 0.0,
    edge_falloff: float = 0.0,
    mapping_gamma: float = 1.0,
    noise_amplitude: float = 0.0,
    noise_frequency: float = 1.0,
    noise_seed: int = 0,
    mapping_curve_points: list[tuple[float, float]] | None = None,
    edge_falloff_mode: str = "linear",
    *,
    options: HeightOptions | None = None,
) -> np.ndarray:
    """Map normalized image intensity to physical height in millimeters."""
    dimensions.validate()
    options = options or HeightOptions()
    options.validate()
    if smoothing_sigma < 0:
        raise ValueError("Smoothing sigma cannot be negative")
    if mapping_gamma <= 0:
        raise ValueError("Height mapping gamma must be positive")
    if noise_amplitude < 0:
        raise ValueError("Noise amplitude cannot be negative")
    if noise_frequency <= 0:
        raise ValueError("Noise frequency must be positive")
    if not 0.0 <= edge_falloff <= 1.0:
        raise ValueError("Edge falloff must be between 0 and 1")
    if edge_falloff_mode not in {"linear", "smoothstep"}:
        raise ValueError("Edge falloff mode must be linear or smoothstep")
    values = np.asarray(image, dtype=np.float32)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("Heightfield input must be finite 2D data")
    if smoothing_sigma > 0 and options.smoothing_strength > 0:
        kernel_size = max(3, int(round(smoothing_sigma * 6)) | 1)
        blurred = cv2.GaussianBlur(values, (kernel_size, kernel_size), smoothing_sigma)
        values = values * (1 - options.smoothing_strength) + blurred * options.smoothing_strength
    if resolution is not None:
        values = resize_heightfield(values, resolution[0], resolution[1])
    values = np.clip(values, 0.0, 1.0)
    if noise_amplitude > 0:
        rows, columns = values.shape
        generator = np.random.default_rng(int(noise_seed) % (1 << 64))
        noise = np.zeros_like(values)
        weight, total = 1.0, 0.0
        for octave in range(options.noise_octaves):
            frequency = noise_frequency * (2**octave)
            grid_rows = max(2, int(round(rows / max(1.0, 32.0 / frequency))))
            grid_columns = max(2, int(round(columns / max(1.0, 32.0 / frequency))))
            coarse = generator.random((grid_rows, grid_columns), dtype=np.float32)
            noise += (cv2.resize(coarse, (columns, rows), interpolation=cv2.INTER_CUBIC) * 2.0 - 1.0) * weight
            total += weight
            weight *= options.noise_persistence
            if weight == 0:
                break
        noise /= total
        values = np.clip(values + noise * noise_amplitude, 0.0, 1.0)
    if edge_falloff > 0:
        rows, columns = values.shape
        row_distance = np.minimum(np.arange(rows), np.arange(rows)[::-1]) / max(1, rows - 1)
        column_distance = np.minimum(np.arange(columns), np.arange(columns)[::-1]) / max(1, columns - 1)
        distance = np.minimum(row_distance[:, None], column_distance[None, :])
        mask = np.clip(distance / max(1e-6, edge_falloff / 2.0), 0.0, 1.0)
        if edge_falloff_mode == "smoothstep":
            mask = mask * mask * (3.0 - 2.0 * mask)
        values *= (1.0 - options.edge_strength + options.edge_strength * mask).astype(np.float32)
    if options.normalize:
        minimum, maximum = float(values.min()), float(values.max())
        values = (values - minimum) / (maximum - minimum) if maximum > minimum else np.zeros_like(values)
    if inverted:
        values = 1.0 - values
    if mapping_curve_points is not None:
        values = apply_curve(values, mapping_curve_points)
    values = np.power(values, 1.0 / mapping_gamma, dtype=np.float32)
    values = np.clip(values, options.clamp_min, options.clamp_max)
    result = dimensions.minimum_height_mm + values * (dimensions.maximum_height_mm - dimensions.minimum_height_mm)
    result = result * options.scale + options.offset_mm
    return result.astype(np.float32)
