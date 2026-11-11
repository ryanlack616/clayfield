"""Serializable source and pipeline descriptors for V2 projects."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from clayfield.field.processing import FieldProcessingSettings
from clayfield.terrain.mapping import MappingSettings

SOURCE_TYPES = {"image", "heightmap", "qfractalnow_config", "fractal_noise", "wave_interference", "mandelbrot", "voronoi", "ridged_noise", "warped_noise", "sdf", "chladni", "spectral", "reaction_diffusion", "phyllotaxis", "cellular_automata", "flow_field", "erosion", "lsystem", "cracks", "penrose", "truchet", "superformula", "gaussian_peaks", "julia", "moire", "gabor", "radial_mask"}
SUPPORTED_ALGORITHM_VERSIONS = {
    "processing": {"1"},
    "mapping": {"1"},
    "fabrication_analysis": {"1"},
    "external_import": {"1"},
}


@dataclass(frozen=True)
class SourceDescriptor:
    """JSON-safe description of an image, procedural, or external source."""

    source_type: str
    parameters: dict[str, Any] = field(default_factory=dict)
    algorithm: str | None = None
    algorithm_version: str | None = None
    seed: int | None = None
    content_hash: str | None = None
    schema_version: int = 1

    def validate(self) -> None:
        if self.source_type not in SOURCE_TYPES:
            raise ValueError(f"Unsupported field source type: {self.source_type}")
        if self.schema_version != 1:
            raise ValueError(f"Unsupported source descriptor schema: {self.schema_version}")
        if not isinstance(self.parameters, dict):
            raise ValueError("Source parameters must be an object")
        if self.seed is not None and (isinstance(self.seed, bool) or not isinstance(self.seed, int)):
            raise ValueError("Source seed must be an integer or None")
        if self.source_type in {"qfractalnow_config", "fractal_noise", "wave_interference", "mandelbrot", "voronoi", "ridged_noise", "warped_noise", "sdf", "chladni", "spectral", "reaction_diffusion", "phyllotaxis", "cellular_automata", "flow_field", "erosion", "lsystem", "cracks", "penrose", "truchet", "superformula", "gaussian_peaks", "julia", "moire", "gabor"} and not self.algorithm:
            raise ValueError("Procedural sources require an algorithm identifier")
        if self.algorithm_version is not None and not self.algorithm_version:
            raise ValueError("Source algorithm version cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "type": self.source_type,
            "schema_version": self.schema_version,
            "parameters": deepcopy(self.parameters),
            "algorithm": self.algorithm,
            "algorithm_version": self.algorithm_version,
            "seed": self.seed,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SourceDescriptor:
        if not isinstance(value, dict):
            raise ValueError("Source descriptor must be an object")
        descriptor = cls(
            source_type=value.get("type", "image"),
            schema_version=value.get("schema_version", 1),
            parameters=deepcopy(value.get("parameters", {})),
            algorithm=value.get("algorithm"),
            algorithm_version=value.get("algorithm_version"),
            seed=value.get("seed"),
            content_hash=value.get("content_hash"),
        )
        descriptor.validate()
        return descriptor


@dataclass(frozen=True)
class PipelineSnapshot:
    """Serializable processing and physical-mapping configuration."""

    source: SourceDescriptor
    processing: dict[str, Any] = field(default_factory=dict)
    secondary_processing: dict[str, Any] = field(default_factory=dict)
    mapping: dict[str, Any] = field(default_factory=dict)
    secondary_source: SourceDescriptor | None = None
    mask_source: SourceDescriptor | None = None
    composition: dict[str, Any] = field(default_factory=dict)
    algorithm_versions: dict[str, str] = field(default_factory=lambda: {
        "processing": "1",
        "mapping": "1",
        "fabrication_analysis": "1",
        "external_import": "1",
    })
    schema_version: int = 1

    def validate(self) -> None:
        if self.schema_version != 1:
            raise ValueError(f"Unsupported pipeline snapshot schema: {self.schema_version}")
        if not isinstance(self.algorithm_versions, dict) or any(not isinstance(key, str) or not isinstance(value, str) or not value for key, value in self.algorithm_versions.items()):
            raise ValueError("Pipeline algorithm versions must be non-empty strings")
        for key, supported in SUPPORTED_ALGORITHM_VERSIONS.items():
            if self.algorithm_versions.get(key, "1") not in supported:
                raise ValueError(f"Unsupported {key} algorithm version")
        self.source.validate()
        if self.secondary_source is not None:
            self.secondary_source.validate()
        if self.mask_source is not None:
            self.mask_source.validate()
        FieldProcessingSettings(**self.processing).validate()
        FieldProcessingSettings(**self.secondary_processing).validate()
        MappingSettings(**self.mapping).validate()
        composition = self.composition or {}
        if composition.get("enabled", False) not in {True, False}:
            raise ValueError("Composition enabled must be boolean")
        if composition.get("operation", "blend") not in {"add", "subtract", "multiply", "minimum", "maximum", "blend"}:
            raise ValueError("Unsupported composition operation")
        amount = composition.get("amount", 1.0)
        if not isinstance(amount, (int, float)) or isinstance(amount, bool) or not 0 <= amount <= 1:
            raise ValueError("Composition amount must be between 0 and 1")
        if composition.get("range_policy", "clip") not in {"clip", "normalize"}:
            raise ValueError("Composition range policy must be clip or normalize")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        processing = asdict(FieldProcessingSettings(**self.processing))
        if processing["resize"] is not None:
            processing["resize"] = list(processing["resize"])
        processing["curve_points"] = [list(point) for point in processing["curve_points"]]
        processing["stage_order"] = list(processing["stage_order"])
        secondary_processing = asdict(FieldProcessingSettings(**self.secondary_processing))
        if secondary_processing["resize"] is not None:
            secondary_processing["resize"] = list(secondary_processing["resize"])
        secondary_processing["curve_points"] = [list(point) for point in secondary_processing["curve_points"]]
        secondary_processing["stage_order"] = list(secondary_processing["stage_order"])
        mapping = asdict(MappingSettings(**self.mapping))
        mapping["mapping_curve_points"] = [list(point) for point in mapping["mapping_curve_points"]]
        return {
            "schema_version": self.schema_version,
            "source": self.source.to_dict(),
            "processing": processing,
            "secondary_processing": secondary_processing,
            "mapping": mapping,
            "secondary_source": self.secondary_source.to_dict() if self.secondary_source is not None else None,
            "mask_source": self.mask_source.to_dict() if self.mask_source is not None else None,
            "composition": deepcopy(self.composition),
            "algorithm_versions": deepcopy(self.algorithm_versions),
        }

    @classmethod
    def from_settings(
        cls,
        source: SourceDescriptor,
        processing: FieldProcessingSettings | None = None,
        mapping: MappingSettings | None = None,
        *,
        secondary_processing: FieldProcessingSettings | None = None,
        secondary_source: SourceDescriptor | None = None,
        mask_source: SourceDescriptor | None = None,
        composition: dict[str, Any] | None = None,
        algorithm_versions: dict[str, str] | None = None,
    ) -> PipelineSnapshot:
        snapshot = cls(
            source=source,
            processing=asdict(processing or FieldProcessingSettings()),
            secondary_processing=asdict(secondary_processing or FieldProcessingSettings()),
            mapping=asdict(mapping or MappingSettings()),
            secondary_source=secondary_source,
            mask_source=mask_source,
            composition=deepcopy(composition or {}),
            algorithm_versions=deepcopy(algorithm_versions or {
                "processing": "1",
                "mapping": "1",
                "fabrication_analysis": "1",
                "external_import": "1",
            }),
        )
        snapshot.validate()
        return snapshot

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> PipelineSnapshot:
        if not isinstance(value, dict):
            raise ValueError("Pipeline snapshot must be an object")
        processing = deepcopy(value.get("processing", {}))
        if processing.get("resize") is not None:
            processing["resize"] = tuple(processing["resize"])
        if "curve_points" in processing:
            processing["curve_points"] = tuple(tuple(point) for point in processing["curve_points"])
        if "stage_order" in processing:
            processing["stage_order"] = tuple(processing["stage_order"])
        secondary_processing = deepcopy(value.get("secondary_processing", {}))
        if secondary_processing.get("resize") is not None:
            secondary_processing["resize"] = tuple(secondary_processing["resize"])
        if "curve_points" in secondary_processing:
            secondary_processing["curve_points"] = tuple(tuple(point) for point in secondary_processing["curve_points"])
        if "stage_order" in secondary_processing:
            secondary_processing["stage_order"] = tuple(secondary_processing["stage_order"])
        mapping = deepcopy(value.get("mapping", {}))
        if "mapping_curve_points" in mapping:
            mapping["mapping_curve_points"] = tuple(tuple(point) for point in mapping["mapping_curve_points"])
        secondary_value = value.get("secondary_source")
        mask_value = value.get("mask_source")
        snapshot = cls(
            schema_version=value.get("schema_version", 1),
            source=SourceDescriptor.from_dict(value.get("source", {})),
            processing=processing,
            secondary_processing=secondary_processing,
            mapping=mapping,
            secondary_source=SourceDescriptor.from_dict(secondary_value) if secondary_value is not None else None,
            mask_source=SourceDescriptor.from_dict(mask_value) if mask_value is not None else None,
            composition=deepcopy(value.get("composition", {})),
            algorithm_versions=deepcopy(value.get("algorithm_versions", {
                "processing": "1",
                "mapping": "1",
                "fabrication_analysis": "1",
                "external_import": "1",
            })),
        )
        snapshot.validate()
        return snapshot


def pipeline_cache_key(snapshot: PipelineSnapshot, shape: tuple[int, int]) -> str:
    """Return a stable cache key for one snapshot at one field resolution."""
    snapshot.validate()
    if len(shape) != 2 or any(isinstance(size, bool) or not isinstance(size, int) or size < 2 for size in shape):
        raise ValueError("Pipeline cache shape must contain two dimensions of at least 2")
    payload = json.dumps(
        {"snapshot": snapshot.to_dict(), "shape": list(shape)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
