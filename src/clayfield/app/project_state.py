"""Central state shared by ClayField UI and processing systems."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class ProjectState:
    """Authoritative state for the currently open project."""

    project_path: Path | None = None
    source_path: Path | None = None
    source_image: np.ndarray | None = None
    source_type: str = "image"
    source_descriptor: dict = field(default_factory=lambda: {"type": "image", "schema_version": 1, "parameters": {}})
    pipeline_snapshot: dict | None = None
    secondary_source_descriptor: dict | None = None
    mask_source_descriptor: dict | None = None
    composition_settings: dict = field(
        default_factory=lambda: {"enabled": False, "operation": "blend", "amount": 1.0, "range_policy": "clip"}
    )
    secondary_processing_settings: dict = field(default_factory=dict)
    secondary_field: np.ndarray | None = None
    secondary_field_name: str | None = None
    mask_field: np.ndarray | None = None
    mask_field_name: str | None = None
    # bytes-like: project_io reads archive members into a bytearray so large
    # members are held once, not once per chunk plus the join copy.
    secondary_original_bytes: bytes | bytearray | None = None
    mask_original_bytes: bytes | bytearray | None = None
    grayscale_image: np.ndarray | None = None
    adjusted_image: np.ndarray | None = None
    inverted: bool = False
    crop_margins: tuple[int, int, int, int] = (0, 0, 0, 0)
    image_resize: tuple[int, int] | None = None
    image_width: int = 0
    image_height: int = 0
    image_bit_depth: int = 0
    dirty: bool = False
    terrain_width_mm: float = 100.0
    terrain_depth_mm: float = 100.0
    minimum_height_mm: float = 0.0
    maximum_height_mm: float = 8.0
    heightfield_resolution: tuple[int, int] | None = (2048, 2048)
    export_resolution: tuple[int, int] = (2048, 2048)
    physical_heightfield: np.ndarray | None = None
    # Sculpting keeps the procedural base and the displacement layer separate so a
    # regeneration can reapply or discard the sculpt explicitly. ``physical_heightfield``
    # is always ``sculpt_base + sculpt_offsets`` while a sculpt layer exists.
    sculpt_base: np.ndarray | None = None
    sculpt_offsets: np.ndarray | None = None
    base_thickness_mm: float = 5.0
    fabrication_profile: dict = field(
        default_factory=lambda: {
            "name": "Generic FDM",
            "minimum_feature_width_mm": 0.4,
            "maximum_slope_degrees": 65.0,
            "high_frequency_limit": 0.15,
        }
    )
    container_mode: str = "none"
    container_wall_thickness_mm: float = 2.0
    container_clearance_mm: float = 2.0
    container_outside_dimensions: bool = True
    relief_mode: str = "positive"
    smoothing_sigma: float = 0.0
    edge_falloff: float = 0.0
    edge_falloff_mode: str = "linear"
    height_mapping_gamma: float = 1.0
    lock_aspect_ratio: bool = True
    noise_amplitude: float = 0.0
    noise_frequency: float = 1.0
    noise_seed: int = 0
    height_invert: bool = False
    height_normalize: bool = False
    height_offset_mm: float = 0.0
    height_scale: float = 1.0
    height_clamp_min: float = 0.0
    height_clamp_max: float = 1.0
    smoothing_strength: float = 1.0
    edge_falloff_strength: float = 1.0
    noise_octaves: int = 1
    noise_persistence: float = 0.5
    adjustment_settings: dict[str, float | bool] = field(default_factory=dict)
    curve_points: list[tuple[float, float]] = field(default_factory=lambda: [(0.0, 0.0), (1.0, 1.0)])
    mapping_curve_points: list[tuple[float, float]] = field(default_factory=lambda: [(0.0, 0.0), (1.0, 1.0)])

    def clear_image(self) -> None:
        """Remove the current image while retaining project settings."""
        self.project_path = None
        self.source_path = None
        self.source_image = None
        self.source_type = "image"
        self.source_descriptor = {"type": "image", "schema_version": 1, "parameters": {}}
        self.pipeline_snapshot = None
        self.secondary_source_descriptor = None
        self.mask_source_descriptor = None
        self.composition_settings = {"enabled": False, "operation": "blend", "amount": 1.0, "range_policy": "clip"}
        self.secondary_processing_settings = {}
        self.secondary_field = None
        self.secondary_field_name = None
        self.mask_field = None
        self.mask_field_name = None
        self.secondary_original_bytes = None
        self.mask_original_bytes = None
        self.grayscale_image = None
        self.adjusted_image = None
        self.inverted = False
        self.image_width = 0
        self.image_height = 0
        self.image_bit_depth = 0
        self.physical_heightfield = None
        self.sculpt_base = None
        self.sculpt_offsets = None
        self.dirty = False

    def set_source(self, path: Path, pixels: np.ndarray) -> None:
        """Set a source image and reset derived image controls."""
        self.source_path = path
        self.source_image = pixels
        self.source_type = "image"
        self.source_descriptor = {"type": "image", "schema_version": 1, "parameters": {}}
        self.pipeline_snapshot = None
        self.secondary_source_descriptor = None
        self.mask_source_descriptor = None
        self.composition_settings = {"enabled": False, "operation": "blend", "amount": 1.0, "range_policy": "clip"}
        self.secondary_processing_settings = {}
        self.secondary_field = None
        self.secondary_field_name = None
        self.mask_field = None
        self.mask_field_name = None
        self.secondary_original_bytes = None
        self.mask_original_bytes = None
        self.grayscale_image = None
        self.adjusted_image = None
        self.physical_heightfield = None
        self.sculpt_base = None
        self.sculpt_offsets = None
        self.inverted = False
        self.image_height, self.image_width = pixels.shape[:2]
        self.image_bit_depth = pixels.dtype.itemsize * 8
        self.dirty = True

    def set_procedural_source(self, descriptor: dict, pipeline_snapshot: dict | None = None) -> None:
        """Set a source that does not require an embedded image."""
        self.project_path = None
        self.source_path = None
        self.source_image = None
        self.source_type = str(descriptor.get("type", ""))
        self.source_descriptor = descriptor.copy()
        self.pipeline_snapshot = pipeline_snapshot.copy() if pipeline_snapshot is not None else None
        self.grayscale_image = None
        self.adjusted_image = None
        self.image_width = 0
        self.image_height = 0
        self.image_bit_depth = 0
        self.physical_heightfield = None
        self.sculpt_base = None
        self.sculpt_offsets = None
        self.dirty = True
