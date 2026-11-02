"""Native .clayfield project persistence."""

from __future__ import annotations

import json
import hashlib
import math
import os
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path

import cv2
import numpy as np

from clayfield.app.project_state import ProjectState
from clayfield.field.persistence import PipelineSnapshot, SourceDescriptor
from clayfield.image.geometry import validate_geometry
from clayfield.terrain.heightfield import options_from_state
from clayfield.terrain.fabrication import FabricationProfile


class ProjectIOError(RuntimeError):
    """Raised for invalid or unreadable ClayField projects."""


CURRENT_PROJECT_VERSION = 4
SUPPORTED_PROJECT_VERSIONS = {1, 2, 3, 4}


def migrate_project_metadata(metadata: dict) -> dict:
    """Upgrade known archive metadata in memory without changing the file."""
    if not isinstance(metadata, dict):
        raise ProjectIOError("Project metadata must be an object")
    version = metadata.get("version", 1)
    if isinstance(version, bool) or not isinstance(version, int) or version not in SUPPORTED_PROJECT_VERSIONS:
        raise ProjectIOError(f"Unsupported ClayField project version: {version}")
    result = deepcopy(metadata)
    if version == 1:
        adjustments = result.get("adjustments", {})
        if not isinstance(adjustments, dict):
            raise ProjectIOError("Project contains invalid adjustments")
        result.setdefault("inverted", bool(adjustments.get("inverted", False)))
        result.setdefault("adjustment_order", list(adjustments))
        result["version"] = 2
        version = 2
    if version == 2:
        result.setdefault("image_geometry", {"crop_margins": [0, 0, 0, 0], "resize": None})
        result["version"] = 3
        version = 3
    if version == 3:
        result.setdefault(
            "source",
            {"type": "image", "schema_version": 1, "parameters": {}, "algorithm": None, "algorithm_version": None, "seed": None, "content_hash": None},
        )
        result.setdefault("pipeline", None)
        result["version"] = 4
    return result


def _parse_resolution(value, field_name: str) -> tuple[int, int] | None:
    """Validate a persisted resolution without allowing malformed metadata through."""
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ProjectIOError(f"Project contains an invalid {field_name}")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise ProjectIOError(f"Project contains an invalid {field_name}")
    if any(not math.isfinite(item) or int(item) != item or int(item) < 2 for item in value):
        raise ProjectIOError(f"Project contains an invalid {field_name}")
    return int(value[0]), int(value[1])


def _parse_curve_points(value, field_name: str) -> list[tuple[float, float]]:
    """Validate normalized curve control points loaded from project metadata."""
    if not isinstance(value, list) or not value:
        raise ProjectIOError(f"Project contains an invalid {field_name}")
    points: list[tuple[float, float]] = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ProjectIOError(f"Project contains an invalid {field_name}")
        x, y = point
        if isinstance(x, bool) or isinstance(y, bool):
            raise ProjectIOError(f"Project contains an invalid {field_name}")
        try:
            normalized = (float(x), float(y))
        except (TypeError, ValueError) as error:
            raise ProjectIOError(f"Project contains an invalid {field_name}") from error
        if any(not math.isfinite(item) or not 0.0 <= item <= 1.0 for item in normalized):
            raise ProjectIOError(f"Project contains an invalid {field_name}")
        points.append(normalized)
    if any(left[0] >= right[0] for left, right in zip(points, points[1:])):
        raise ProjectIOError(f"Project contains non-increasing {field_name}")
    return points


def save_project(state: ProjectState, path: str | Path, *, update_state: bool = True) -> Path:
    """Save an image-backed or procedural project in a ZIP archive."""
    try:
        descriptor = SourceDescriptor.from_dict(state.source_descriptor)
    except (TypeError, ValueError) as error:
        raise ProjectIOError(f"Invalid field source descriptor: {error}") from error
    if descriptor.source_type != state.source_type:
        raise ProjectIOError("Project source type does not match its descriptor")
    if descriptor.source_type == "image" and (state.source_image is None or state.source_path is None):
        raise ProjectIOError("An image source requires source pixels and a source path")
    pipeline = None
    if state.pipeline_snapshot is not None:
        try:
            pipeline = PipelineSnapshot.from_dict(state.pipeline_snapshot).to_dict()
        except (TypeError, ValueError) as error:
            raise ProjectIOError(f"Invalid pipeline snapshot: {error}") from error
    secondary_encoded = None
    if state.secondary_field is not None:
        values = np.asarray(state.secondary_field, dtype=np.float32)
        if values.ndim != 2 or min(values.shape, default=0) < 2 or not np.isfinite(values).all() or float(values.min()) < 0 or float(values.max()) > 1:
            raise ProjectIOError("Secondary field must be finite normalized 2D data")
        secondary_encoded = np.rint(values * 65535.0).astype(np.uint16)
    mask_encoded = None
    if state.mask_field is not None:
        values = np.asarray(state.mask_field, dtype=np.float32)
        if values.ndim != 2 or min(values.shape, default=0) < 2 or not np.isfinite(values).all() or float(values.min()) < 0 or float(values.max()) > 1:
            raise ProjectIOError("Mask field must be finite normalized 2D data")
        mask_encoded = np.rint(values * 65535.0).astype(np.uint16)
    output = Path(path).expanduser()
    if output.suffix.lower() != ".clayfield":
        output = output.with_suffix(".clayfield")
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = None
    extension = ".png"
    if state.source_image is not None:
        # Use lossless encoding regardless of the original filename. JPEG
        # re-encoding would change the source on every save.
        try:
            success, encoded = cv2.imencode(extension, state.source_image)
        except cv2.error as error:
            raise ProjectIOError(f"Could not encode the source image: {error}") from error
        if not success:
            raise ProjectIOError("Could not encode the source image")
        descriptor = SourceDescriptor(
            source_type=descriptor.source_type,
            schema_version=descriptor.schema_version,
            parameters=descriptor.parameters,
            algorithm=descriptor.algorithm,
            algorithm_version=descriptor.algorithm_version,
            seed=descriptor.seed,
            content_hash=hashlib.sha256(np.asarray(state.source_image).tobytes()).hexdigest(),
        )
    metadata = {
        "version": CURRENT_PROJECT_VERSION,
        "source_name": state.source_path.name if state.source_path is not None else None,
        "source": descriptor.to_dict(),
        "pipeline": pipeline,
        "inverted": state.inverted,
        "adjustment_order": list(state.adjustment_settings),
        "image_geometry": {"crop_margins": state.crop_margins, "resize": state.image_resize},
        "terrain": {
            "width_mm": state.terrain_width_mm,
            "depth_mm": state.terrain_depth_mm,
            "minimum_height_mm": state.minimum_height_mm,
            "maximum_height_mm": state.maximum_height_mm,
            "base_thickness_mm": state.base_thickness_mm,
            "fabrication_profile": state.fabrication_profile,
            "container": {
                "mode": state.container_mode,
                "wall_thickness_mm": state.container_wall_thickness_mm,
                "clearance_mm": state.container_clearance_mm,
                "outside_dimensions": state.container_outside_dimensions,
            },
            "smoothing_sigma": state.smoothing_sigma,
            "edge_falloff": state.edge_falloff,
            "edge_falloff_mode": state.edge_falloff_mode,
            "height_mapping_gamma": state.height_mapping_gamma,
            "lock_aspect_ratio": state.lock_aspect_ratio,
            "noise_amplitude": state.noise_amplitude,
            "noise_frequency": state.noise_frequency,
            "noise_seed": state.noise_seed,
            "noise_octaves": state.noise_octaves,
            "noise_persistence": state.noise_persistence,
            "height_invert": state.height_invert,
            "height_normalize": state.height_normalize,
            "height_offset_mm": state.height_offset_mm,
            "height_scale": state.height_scale,
            "height_clamp_min": state.height_clamp_min,
            "height_clamp_max": state.height_clamp_max,
            "smoothing_strength": state.smoothing_strength,
            "edge_falloff_strength": state.edge_falloff_strength,
            "relief_mode": state.relief_mode,
            "resolution": state.heightfield_resolution,
            "export_resolution": state.export_resolution,
        },
        "adjustments": state.adjustment_settings,
        "curve_points": state.curve_points,
        "mapping_curve_points": state.mapping_curve_points,
    }
    temporary = None
    try:
        fd, name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
        os.close(fd)
        temporary = Path(name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("project.json", json.dumps(metadata, indent=2))
            if encoded is not None:
                archive.writestr(f"source_image{extension}", encoded.tobytes())
            if secondary_encoded is not None:
                success, secondary_png = cv2.imencode(".png", secondary_encoded)
                if not success:
                    raise ProjectIOError("Could not encode the secondary field")
                archive.writestr("secondary_field.png", secondary_png.tobytes())
            if mask_encoded is not None:
                success, mask_png = cv2.imencode(".png", mask_encoded)
                if not success:
                    raise ProjectIOError("Could not encode the mask field")
                archive.writestr("mask_field.png", mask_png.tobytes())
            if state.secondary_original_bytes is not None:
                archive.writestr("secondary_original.bin", state.secondary_original_bytes)
            if state.mask_original_bytes is not None:
                archive.writestr("mask_original.bin", state.mask_original_bytes)
        temporary.replace(output)
    except OSError as error:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise ProjectIOError(f"Could not atomically save project: {error}") from error
    if update_state:
        state.project_path = output
        state.dirty = False
    return output


def autosave_project(state: ProjectState, path: str | Path) -> Path:
    """Write a recovery snapshot without changing the active project state."""
    return save_project(state, path, update_state=False)


def load_project(path: str | Path, state: ProjectState) -> Path:
    """Load a project transactionally, preserving the active state on failure."""
    loaded = ProjectState()
    try:
        result = _load_project(path, loaded)
    except ProjectIOError:
        raise
    except (ValueError, TypeError, AttributeError, OverflowError, cv2.error) as error:
        raise ProjectIOError(f"Invalid ClayField project: {error}") from error
    state.__dict__.update(loaded.__dict__)
    return result


def _load_project(path: str | Path, state: ProjectState) -> Path:
    project_path = Path(path).expanduser()
    secondary_original_bytes = None
    mask_original_bytes = None
    try:
        with zipfile.ZipFile(project_path) as archive:
            metadata = migrate_project_metadata(json.loads(archive.read("project.json")))
            descriptor = SourceDescriptor.from_dict(metadata.get("source", {}))
            image_names = [name for name in archive.namelist() if name.startswith("source_image.")]
            secondary_names = [name for name in archive.namelist() if name == "secondary_field.png"]
            mask_names = [name for name in archive.namelist() if name == "mask_field.png"]
            secondary_original_names = [name for name in archive.namelist() if name == "secondary_original.bin"]
            mask_original_names = [name for name in archive.namelist() if name == "mask_original.bin"]
            secondary_original_bytes = archive.read(secondary_original_names[0]) if secondary_original_names else None
            mask_original_bytes = archive.read(mask_original_names[0]) if mask_original_names else None
            pixels = None
            if descriptor.source_type == "image":
                if not image_names:
                    raise ProjectIOError("Image project does not contain a source image")
                pixels = cv2.imdecode(np.frombuffer(archive.read(image_names[0]), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                if pixels is None:
                    raise ProjectIOError("Embedded source image could not be decoded")
            secondary_field = None
            if secondary_names:
                secondary_field = cv2.imdecode(np.frombuffer(archive.read(secondary_names[0]), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                if secondary_field is None or secondary_field.ndim != 2:
                    raise ProjectIOError("Embedded secondary field could not be decoded")
                secondary_maximum = 65535.0 if secondary_field.dtype == np.uint16 else 255.0
                secondary_field = np.asarray(secondary_field, dtype=np.float32) / secondary_maximum
            mask_field = None
            if mask_names:
                mask_field = cv2.imdecode(np.frombuffer(archive.read(mask_names[0]), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                if mask_field is None or mask_field.ndim != 2:
                    raise ProjectIOError("Embedded mask field could not be decoded")
                mask_maximum = 65535.0 if mask_field.dtype == np.uint16 else 255.0
                mask_field = np.asarray(mask_field, dtype=np.float32) / mask_maximum
    except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError) as error:
        raise ProjectIOError(f"Invalid ClayField project: {error}") from error

    terrain = metadata.get("terrain", {})
    image_geometry = metadata.get("image_geometry", {})
    margins = image_geometry.get("crop_margins", [0, 0, 0, 0])
    resize = image_geometry.get("resize")
    validate_geometry(margins, resize)
    state.crop_margins = tuple(margins)
    state.image_resize = tuple(resize) if resize is not None else None
    state.project_path = project_path
    state.source_type = descriptor.source_type
    state.source_descriptor = descriptor.to_dict()
    state.pipeline_snapshot = None
    state.secondary_source_descriptor = None
    state.mask_source_descriptor = None
    state.composition_settings = {"enabled": False, "operation": "blend", "amount": 1.0, "range_policy": "clip"}
    if metadata.get("pipeline") is not None:
        try:
            restored_pipeline = PipelineSnapshot.from_dict(metadata["pipeline"])
            state.pipeline_snapshot = restored_pipeline.to_dict()
            state.secondary_source_descriptor = restored_pipeline.secondary_source.to_dict() if restored_pipeline.secondary_source is not None else None
            state.mask_source_descriptor = restored_pipeline.mask_source.to_dict() if restored_pipeline.mask_source is not None else None
            state.composition_settings = dict(restored_pipeline.composition)
            state.secondary_processing_settings = dict(restored_pipeline.secondary_processing)
        except (TypeError, ValueError) as error:
            raise ProjectIOError(f"Project contains an invalid pipeline snapshot: {error}") from error
    state.source_path = Path(metadata.get("source_name", image_names[0])) if pixels is not None else None
    state.source_image = pixels
    state.secondary_field = secondary_field
    if state.secondary_field is not None:
        state.secondary_field.setflags(write=False)
    state.secondary_field_name = secondary_names[0] if secondary_field is not None else None
    state.secondary_original_bytes = secondary_original_bytes
    state.mask_field = mask_field
    if state.mask_field is not None:
        state.mask_field.setflags(write=False)
    state.mask_field_name = mask_names[0] if mask_field is not None else None
    state.mask_original_bytes = mask_original_bytes
    state.grayscale_image = None
    state.adjusted_image = None
    state.physical_heightfield = None
    state.terrain_width_mm = float(terrain.get("width_mm", 100.0))
    state.terrain_depth_mm = float(terrain.get("depth_mm", 100.0))
    state.minimum_height_mm = float(terrain.get("minimum_height_mm", 0.0))
    state.maximum_height_mm = float(terrain.get("maximum_height_mm", 8.0))
    state.base_thickness_mm = float(terrain.get("base_thickness_mm", 5.0))
    container = terrain.get("container", {})
    state.container_mode = container.get("mode", "none")
    state.container_wall_thickness_mm = float(container.get("wall_thickness_mm", 2.0))
    state.container_clearance_mm = float(container.get("clearance_mm", 2.0))
    state.container_outside_dimensions = bool(container.get("outside_dimensions", True))
    try:
        state.fabrication_profile = FabricationProfile(**terrain.get("fabrication_profile", {})).__dict__.copy()
    except (TypeError, ValueError) as error:
        raise ProjectIOError(f"Project contains an invalid fabrication profile: {error}") from error
    state.smoothing_sigma = float(terrain.get("smoothing_sigma", 0.0))
    state.edge_falloff = float(terrain.get("edge_falloff", 0.0))
    state.edge_falloff_mode = terrain.get("edge_falloff_mode", "linear")
    if state.edge_falloff_mode not in {"linear", "smoothstep"}:
        raise ProjectIOError("Project contains an invalid edge falloff mode")
    state.height_mapping_gamma = float(terrain.get("height_mapping_gamma", 1.0))
    state.lock_aspect_ratio = bool(terrain.get("lock_aspect_ratio", True))
    state.noise_amplitude = float(terrain.get("noise_amplitude", 0.0))
    state.noise_frequency = float(terrain.get("noise_frequency", 1.0))
    state.noise_seed = int(terrain.get("noise_seed", 0))
    state.noise_octaves = terrain.get("noise_octaves", 1)
    state.noise_persistence = float(terrain.get("noise_persistence", 0.5))
    state.height_invert = bool(terrain.get("height_invert", False))
    state.height_normalize = bool(terrain.get("height_normalize", False))
    state.height_offset_mm = float(terrain.get("height_offset_mm", 0.0))
    state.height_scale = float(terrain.get("height_scale", 1.0))
    state.height_clamp_min = float(terrain.get("height_clamp_min", 0.0))
    state.height_clamp_max = float(terrain.get("height_clamp_max", 1.0))
    state.smoothing_strength = float(terrain.get("smoothing_strength", 1.0))
    state.edge_falloff_strength = float(terrain.get("edge_falloff_strength", 1.0))
    options_from_state(state).validate()
    if state.height_mapping_gamma <= 0:
        raise ProjectIOError("Project contains an invalid height mapping gamma")
    if state.noise_amplitude < 0 or state.noise_frequency <= 0:
        raise ProjectIOError("Project contains invalid noise settings")
    state.relief_mode = terrain.get("relief_mode", "positive")
    if state.relief_mode not in {"positive", "negative"}:
        raise ProjectIOError("Project contains an invalid relief mode")
    if state.terrain_width_mm <= 0 or state.terrain_depth_mm <= 0 or state.base_thickness_mm <= 0:
        raise ProjectIOError("Project contains invalid physical dimensions")
    if not all(math.isfinite(value) for value in (state.terrain_width_mm, state.terrain_depth_mm, state.minimum_height_mm, state.maximum_height_mm, state.base_thickness_mm, state.smoothing_sigma, state.edge_falloff, state.height_mapping_gamma, state.noise_amplitude, state.noise_frequency)):
        raise ProjectIOError("Project contains non-finite settings")
    if state.minimum_height_mm > state.maximum_height_mm or state.smoothing_sigma < 0 or not 0 <= state.edge_falloff <= 1:
        raise ProjectIOError("Project contains invalid height or terrain settings")
    adjustment_settings = dict(metadata.get("adjustments", {}))
    adjustment_order = metadata.get("adjustment_order")
    if adjustment_order:
        ordered = {name: adjustment_settings[name] for name in adjustment_order if name in adjustment_settings}
        ordered.update({name: value for name, value in adjustment_settings.items() if name not in ordered})
        adjustment_settings = ordered
    state.adjustment_settings = adjustment_settings
    state.inverted = bool(metadata.get("inverted", adjustment_settings.get("inverted", False)))
    state.adjustment_settings["inverted"] = state.inverted
    state.curve_points = _parse_curve_points(
        metadata.get("curve_points", [(0.0, 0.0), (1.0, 1.0)]),
        "curve points",
    )
    state.mapping_curve_points = _parse_curve_points(
        metadata.get("mapping_curve_points", [(0.0, 0.0), (1.0, 1.0)]),
        "mapping curve points",
    )
    state.heightfield_resolution = _parse_resolution(terrain.get("resolution"), "heightfield resolution")
    state.export_resolution = _parse_resolution(
        terrain.get("export_resolution", [2048, 2048]),
        "export resolution",
    ) or (2048, 2048)
    if pixels is not None:
        state.image_height, state.image_width = pixels.shape[:2]
        state.image_bit_depth = pixels.dtype.itemsize * 8
        content_hash = hashlib.sha256(np.asarray(pixels).tobytes()).hexdigest()
        if descriptor.content_hash is not None and descriptor.content_hash != content_hash:
            raise ProjectIOError("Embedded source image does not match its content hash")
    else:
        state.image_height = state.image_width = state.image_bit_depth = 0
    state.dirty = False
    return project_path
