"""Contracts for V2 normalized height fields.

The field layer deliberately has no Qt, image, mesh, or GPU dependencies. A
normalized field is the hand-off between source generation and physical terrain
mapping.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FieldMetadata:
    """Provenance and coordinate contract for a normalized field."""

    source_type: str
    algorithm: str
    algorithm_version: str = "1"
    seed: int | None = None
    tileable: bool = False
    coordinate_convention: str = "vertex_lattice"

    def validate(self) -> None:
        if not self.source_type or not self.algorithm or not self.algorithm_version:
            raise ValueError("Field metadata identifiers cannot be empty")
        if self.coordinate_convention != "vertex_lattice":
            raise ValueError("Unsupported field coordinate convention")
        if self.seed is not None and (isinstance(self.seed, bool) or not isinstance(self.seed, int)):
            raise ValueError("Field seed must be an integer or None")


def validate_normalized_field(field: np.ndarray, *, allow_out_of_range: bool = False) -> np.ndarray:
    """Validate a field and return it as a float32 array.

    Published normalized fields are bounded to ``0..1``. Intermediate field
    operations may opt into range validation being deferred, but they must still
    be finite and two-dimensional.
    """
    values = np.asarray(field)
    if values.ndim != 2 or min(values.shape, default=0) < 2:
        raise ValueError("Normalized field must be at least a 2D 2x2 array")
    if not np.issubdtype(values.dtype, np.floating):
        raise ValueError("Normalized field must use a floating-point dtype")
    if not np.isfinite(values).all():
        raise ValueError("Normalized field must contain only finite values")
    if not allow_out_of_range and (float(values.min()) < 0.0 or float(values.max()) > 1.0):
        raise ValueError("Normalized field values must be between 0 and 1")
    return values.astype(np.float32, copy=False)


@dataclass(frozen=True)
class NormalizedField:
    """Immutable published field with reproducibility metadata."""

    values: np.ndarray
    metadata: FieldMetadata

    def __post_init__(self) -> None:
        self.metadata.validate()
        values = validate_normalized_field(self.values)
        # Copy before marking read-only so callers cannot mutate a producer's
        # working buffer through the field contract.
        values = np.array(values, dtype=np.float32, copy=True)
        values.setflags(write=False)
        object.__setattr__(self, "values", values)

    @property
    def shape(self) -> tuple[int, int]:
        return self.values.shape

    @property
    def minimum(self) -> float:
        return float(self.values.min())

    @property
    def maximum(self) -> float:
        return float(self.values.max())
