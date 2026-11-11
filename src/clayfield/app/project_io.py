"""Native .clayfield project persistence."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import warnings
import zipfile
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from clayfield.app.project_state import ProjectState
from clayfield.field.persistence import PipelineSnapshot, SourceDescriptor
from clayfield.image.geometry import validate_geometry
from clayfield.image.loader import ImageLoadError, load_image_bytes
from clayfield.resource_budget import MAX_ABSOLUTE_RESOLUTION_DIMENSION
from clayfield.terrain.fabrication import FabricationProfile
from clayfield.terrain.heightfield import options_from_state


class ProjectIOError(RuntimeError):
    """Raised for invalid or unreadable ClayField projects."""


CURRENT_PROJECT_VERSION = 4
SUPPORTED_PROJECT_VERSIONS = {1, 2, 3, 4}

# Archive safety limits. These are security controls against malformed or
# malicious `.clayfield` archives, not fabrication mesh limits. They are sized
# for the project's 32 GB target machine: a 16384x16384 16-bit source image is
# roughly 0.5 GiB as PNG, so a 1 GiB per-member ceiling leaves generous headroom
# for legitimate large projects while still bounding a single decompression.
#
# Deliberate adjustments from the suggested starting values:
#   * per-member ceiling kept at 1 GiB (suggested value); a 16384^2 RGB PNG is
#     well under this, and raw `.bin` sidecar fields are typically far smaller.
#   * total uncompressed kept at 4 GiB (suggested value).
#   * compression ratio kept at 1000:1 (suggested value); legitimate PNG/ZIP
#     project members compress at close to 1:1 because PNG is already packed.
ARCHIVE_COMPRESSED_WARNING_BYTES = 512 * 1024 * 1024
ARCHIVE_COMPRESSED_HARD_LIMIT_BYTES = 2 * 1024 * 1024 * 1024
ARCHIVE_TOTAL_UNCOMPRESSED_LIMIT_BYTES = 4 * 1024 * 1024 * 1024
ARCHIVE_MEMBER_LIMIT_BYTES = 1024 * 1024 * 1024
ARCHIVE_PROJECT_JSON_LIMIT_BYTES = 16 * 1024 * 1024
ARCHIVE_MAX_MEMBERS = 32
ARCHIVE_MAX_COMPRESSION_RATIO = 1000

# Absolute, non-overridable allocation-safety ceiling for persisted resolution
# dimensions. This is NOT a fabrication budget and NOT a 2048/4096 preset cap:
# it exists only to reject metadata that would request impossible allocations.
# 16384 is the common maximum 2D texture dimension on desktop GPUs and is
# ~1 GiB per float32 plane, a defensible single-allocation ceiling on a 32 GB
# machine. It deliberately cannot be raised from the environment: a project file
# is untrusted input, so its metadata bounds must not depend on process config.
# Preview resolution and fabrication resolution remain separate fields and are
# validated independently against this same absolute ceiling. The constant is
# defined in clayfield.resource_budget; this module re-exports it so callers and
# tests can import the ceiling from either place without a second definition.
MAX_ABSOLUTE_RESOLUTION_DIMENSION = MAX_ABSOLUTE_RESOLUTION_DIMENSION


@dataclass(frozen=True)
class ArchiveLimits:
    """Configurable bounds for one project archive."""

    max_members: int = ARCHIVE_MAX_MEMBERS
    max_compressed_bytes: int = ARCHIVE_COMPRESSED_HARD_LIMIT_BYTES
    compressed_warning_bytes: int = ARCHIVE_COMPRESSED_WARNING_BYTES
    max_member_bytes: int = ARCHIVE_MEMBER_LIMIT_BYTES
    max_total_uncompressed_bytes: int = ARCHIVE_TOTAL_UNCOMPRESSED_LIMIT_BYTES
    max_project_json_bytes: int = ARCHIVE_PROJECT_JSON_LIMIT_BYTES
    max_compression_ratio: int = ARCHIVE_MAX_COMPRESSION_RATIO


DEFAULT_ARCHIVE_LIMITS = ArchiveLimits()

_ALLOWED_MEMBERS = {
    "project.json",
    "secondary_field.png",
    "mask_field.png",
    "secondary_original.bin",
    "mask_original.bin",
}
_ALLOWED_SOURCE_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def _max_resolution_dimension() -> int:
    """Return the absolute allocation-safety ceiling for resolution metadata.

    Deliberately not environment-configurable: a persisted project file is
    untrusted input and must not be able to raise its own validation bound.
    """
    return MAX_ABSOLUTE_RESOLUTION_DIMENSION


def _is_allowed_member(name: str) -> bool:
    """Return whether an archive member is part of the documented format."""
    if name in _ALLOWED_MEMBERS:
        return True
    if name.startswith("source_image."):
        suffix = name[len("source_image."):].lower()
        return f".{suffix}" in _ALLOWED_SOURCE_IMAGE_EXTENSIONS
    return False


def _is_suspicious_member_name(name: str) -> bool:
    """Reject absolute, traversal, backslash, NUL, or empty member names."""
    if not name or "\x00" in name or "\\" in name:
        return True
    if name.startswith("/") or name.startswith("../") or name == "..":
        return True
    return ".." in name.split("/")


def _validate_archive(
    archive: zipfile.ZipFile,
    archive_path: Path,
    limits: ArchiveLimits | None = None,
    *,
    compressed_size: int | None = None,
) -> dict[str, zipfile.ZipInfo]:
    """Validate archive structure and sizes before any member is decompressed.

    ``compressed_size`` may be supplied when the caller already stat'ed the file
    (see :func:`_precheck_archive_size`), which lets a huge archive be rejected
    before ``ZipFile`` parses its central directory. Metadata is checked here,
    but callers must still enforce actual bytes read through
    :func:`_read_member`, because ZIP headers can lie about sizes.
    """
    active = limits or DEFAULT_ARCHIVE_LIMITS
    if compressed_size is None:
        try:
            compressed_size = archive_path.stat().st_size
        except OSError as error:
            raise ProjectIOError(f"Could not inspect ClayField project archive: {error}") from error
    if compressed_size > active.max_compressed_bytes:
        raise ProjectIOError(
            f"ClayField project archive is too large ({compressed_size} bytes; limit {active.max_compressed_bytes})"
        )
    if compressed_size > active.compressed_warning_bytes:
        warnings.warn(
            f"ClayField project archive is large ({compressed_size} bytes); loading may be slow",
            RuntimeWarning,
            stacklevel=2,
        )
    try:
        infos = archive.infolist()
    except (OSError, zipfile.BadZipFile) as error:
        raise ProjectIOError(f"Invalid ClayField project archive: {error}") from error
    if len(infos) > active.max_members:
        raise ProjectIOError(
            f"ClayField project archive contains too many members ({len(infos)}; limit {active.max_members})"
        )
    names = [info.filename for info in infos]
    if len(set(names)) != len(names):
        duplicates = sorted({name for name in names if names.count(name) > 1})
        raise ProjectIOError(f"ClayField project archive contains duplicate members: {duplicates}")
    members: dict[str, zipfile.ZipInfo] = {}
    total_uncompressed = 0
    for info in infos:
        name = info.filename
        if info.is_dir():
            raise ProjectIOError(f"ClayField project archive contains a directory entry: {name}")
        if _is_suspicious_member_name(name):
            raise ProjectIOError(f"ClayField project archive contains an unsafe member name: {name!r}")
        if not _is_allowed_member(name):
            raise ProjectIOError(f"ClayField project archive contains an unexpected member: {name}")
        if info.flag_bits & 0x1:
            raise ProjectIOError(f"ClayField project archive member is encrypted: {name}")
        if info.file_size < 0 or info.compress_size < 0:
            raise ProjectIOError(f"ClayField project archive member has an invalid size: {name}")
        member_limit = active.max_project_json_bytes if name == "project.json" else active.max_member_bytes
        if info.file_size > member_limit:
            raise ProjectIOError(
                f"ClayField project archive member is too large: {name} ({info.file_size} bytes; limit {member_limit})"
            )
        if info.file_size > 0 and info.compress_size == 0:
            raise ProjectIOError(f"ClayField project archive member has inconsistent sizes: {name}")
        ratio = info.file_size / max(info.compress_size, 1)
        if ratio > active.max_compression_ratio:
            raise ProjectIOError(
                f"ClayField project archive member has a suspicious compression ratio: {name} ({ratio:.0f}:1; limit {active.max_compression_ratio}:1)"
            )
        total_uncompressed += info.file_size
        if total_uncompressed > active.max_total_uncompressed_bytes:
            raise ProjectIOError(
                f"ClayField project archive expands beyond the limit ({total_uncompressed} bytes; limit {active.max_total_uncompressed_bytes})"
            )
        members[name] = info
    if "project.json" not in members:
        raise ProjectIOError("ClayField project archive does not contain project.json")
    return members


def _read_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int, field_name: str) -> bytearray:
    """Read one archive member into a single bounded buffer.

    The previous implementation collected 1 MiB chunks in a list and joined
    them, which held two copies of a 1 GiB member at the peak. A preallocated
    bytearray holds one copy and the read loop fills it in place. The return
    type is ``bytearray`` (a bytes-like object); callers pass it to
    ``json.loads``, ``hashlib``, ``cv2.imdecode``, and ``zipfile.writestr``,
    all of which accept it without another copy.
    """
    if info.file_size > limit:
        raise ProjectIOError(f"ClayField project {field_name} is too large ({info.file_size} bytes; limit {limit})")
    buffer = bytearray(info.file_size)
    view = memoryview(buffer)
    total = 0
    try:
        with archive.open(info) as member:
            while total < len(buffer):
                chunk = member.read(min(1024 * 1024, len(buffer) - total))
                if not chunk:
                    break
                view[total:total + len(chunk)] = chunk
                total += len(chunk)
                if total > limit:
                    raise ProjectIOError(
                        f"ClayField project {field_name} exceeds its size limit while decompressing ({limit} bytes)"
                    )
            # A ZIP header can understate the member size. If the reader can
            # still produce a byte after the declared length, the archive lied.
            if total < len(buffer) or member.read(1):
                raise ProjectIOError(
                    f"ClayField project {field_name} size does not match its archive metadata ({total} != {info.file_size})"
                )
    except ProjectIOError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        raise ProjectIOError(f"Could not read ClayField project {field_name}: {error}") from error
    return buffer


def _precheck_archive_size(archive_path: Path, limits: ArchiveLimits) -> int:
    """Reject an oversize archive before ZipFile parses its central directory."""
    try:
        compressed_size = archive_path.stat().st_size
    except OSError as error:
        raise ProjectIOError(f"Could not inspect ClayField project archive: {error}") from error
    if compressed_size > limits.max_compressed_bytes:
        raise ProjectIOError(
            f"ClayField project archive is too large ({compressed_size} bytes; limit {limits.max_compressed_bytes})"
        )
    return compressed_size


def _decode_archive_image(data, name: str, field_name: str) -> np.ndarray:
    """Decode an archive image through the same budget as a normal load.

    Archive members are untrusted input. ``load_image_bytes`` enforces the
    decoded-memory budget and channel rules that ``load_image`` applies to a
    file, and this wrapper adds the absolute per-axis allocation ceiling. The
    old code called ``cv2.imdecode`` directly, so a small archive member could
    decode to a multi-gigabyte image before anything checked its size.
    """
    try:
        loaded = load_image_bytes(data, name=name)
    except ImageLoadError as error:
        raise ProjectIOError(f"Embedded {field_name} could not be decoded: {error}") from error
    height, width = loaded.pixels.shape[:2]
    if max(width, height) > MAX_ABSOLUTE_RESOLUTION_DIMENSION:
        raise ProjectIOError(
            f"Embedded {field_name} is {width} x {height}; the absolute "
            f"allocation limit is {MAX_ABSOLUTE_RESOLUTION_DIMENSION} per axis"
        )
    return loaded.pixels


def _array_sha256(values: np.ndarray) -> str:
    """Hash array bytes without forcing an extra copy when already contiguous."""
    contiguous = np.ascontiguousarray(values)
    return hashlib.sha256(contiguous).hexdigest()


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
    """Validate a persisted resolution without allowing malformed metadata through.

    This validates metadata only: values must be structurally valid, finite,
    positive integers. It deliberately does not enforce a fabrication budget.
    The upper bound exists solely to reject impossible allocation requests and
    is the absolute, non-overridable ``MAX_ABSOLUTE_RESOLUTION_DIMENSION``.
    """
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ProjectIOError(f"Project contains an invalid {field_name}")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise ProjectIOError(f"Project contains an invalid {field_name}")
    if any(not math.isfinite(item) or int(item) != item or int(item) < 2 for item in value):
        raise ProjectIOError(f"Project contains an invalid {field_name}")
    maximum = _max_resolution_dimension()
    resolution = (int(value[0]), int(value[1]))
    if any(item > maximum for item in resolution):
        raise ProjectIOError(
            f"Project contains an implausible {field_name} {resolution}; "
            f"absolute limit is {maximum} per axis"
        )
    return resolution


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
    # strict=False is required here: the second sequence is one element shorter
    # by construction, so zip(strict=True) would always raise.
    if any(left[0] >= right[0] for left, right in zip(points, points[1:], strict=False)):
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
            content_hash=_array_sha256(np.asarray(state.source_image)),
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
    limits = DEFAULT_ARCHIVE_LIMITS
    try:
        # Reject an oversize archive before ZipFile parses its central
        # directory. _validate_archive reuses this size instead of stat'ing.
        compressed_size = _precheck_archive_size(project_path, limits)
        with zipfile.ZipFile(project_path) as archive:
            members = _validate_archive(archive, project_path, limits, compressed_size=compressed_size)
            metadata_bytes = _read_member(
                archive, members["project.json"], limits.max_project_json_bytes, "project.json"
            )
            metadata = migrate_project_metadata(json.loads(metadata_bytes))
            descriptor = SourceDescriptor.from_dict(metadata.get("source", {}))
            image_names = [name for name in members if name.startswith("source_image.")]
            secondary_names = [name for name in members if name == "secondary_field.png"]
            mask_names = [name for name in members if name == "mask_field.png"]
            secondary_original_names = [name for name in members if name == "secondary_original.bin"]
            mask_original_names = [name for name in members if name == "mask_original.bin"]
            secondary_original_bytes = (
                _read_member(archive, members[secondary_original_names[0]], limits.max_member_bytes, "secondary original field")
                if secondary_original_names
                else None
            )
            mask_original_bytes = (
                _read_member(archive, members[mask_original_names[0]], limits.max_member_bytes, "mask original field")
                if mask_original_names
                else None
            )
            pixels = None
            if descriptor.source_type == "image":
                if not image_names:
                    raise ProjectIOError("Image project does not contain a source image")
                image_bytes = _read_member(archive, members[image_names[0]], limits.max_member_bytes, "source image")
                pixels = _decode_archive_image(image_bytes, image_names[0], "source image")
            secondary_field = None
            if secondary_names:
                secondary_bytes = _read_member(
                    archive, members[secondary_names[0]], limits.max_member_bytes, "secondary field"
                )
                secondary_field = _decode_archive_image(secondary_bytes, secondary_names[0], "secondary field")
                if secondary_field.ndim != 2:
                    raise ProjectIOError("Embedded secondary field could not be decoded as 2D data")
                secondary_maximum = 65535.0 if secondary_field.dtype == np.uint16 else 255.0
                secondary_field = np.asarray(secondary_field, dtype=np.float32) / secondary_maximum
            mask_field = None
            if mask_names:
                mask_bytes = _read_member(archive, members[mask_names[0]], limits.max_member_bytes, "mask field")
                mask_field = _decode_archive_image(mask_bytes, mask_names[0], "mask field")
                if mask_field.ndim != 2:
                    raise ProjectIOError("Embedded mask field could not be decoded as 2D data")
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
        content_hash = _array_sha256(np.asarray(pixels))
        if descriptor.content_hash is not None and descriptor.content_hash != content_hash:
            raise ProjectIOError("Embedded source image does not match its content hash")
    else:
        state.image_height = state.image_width = state.image_bit_depth = 0
    state.dirty = False
    return project_path
