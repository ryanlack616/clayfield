"""Contour-band modifier for scalar normalized fields."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from clayfield.app.cancellation import check_cancelled
from clayfield.field.model import FieldMetadata, NormalizedField


@dataclass(frozen=True)
class ContourParameters:
    bands: int = 12
    line_width: float = 0.2
    invert: bool = False

    def validate(self) -> None:
        if isinstance(self.bands, bool) or not 1 <= self.bands <= 256 or not np.isfinite(self.line_width) or not 0 < self.line_width <= 1:
            raise ValueError("Contour parameters are invalid")


def apply_contours(field: NormalizedField, parameters: ContourParameters | None = None, *, cancel_check=None) -> NormalizedField:
    """Convert a scalar field into raised contour bands."""
    parameters = parameters or ContourParameters()
    parameters.validate()
    check_cancelled(cancel_check)
    phase = (field.values * parameters.bands) % 1.0
    distance = np.minimum(phase, 1.0 - phase)
    values = np.clip(1.0 - distance / parameters.line_width, 0.0, 1.0)
    if parameters.invert:
        values = 1.0 - values
    return NormalizedField(values.astype(np.float32), FieldMetadata("contours", "contour_bands", "1"))
