"""Brush settings for the sculpting subsystem.

The defaults follow the sculpting handoff: a radius of 5 % of the model width is
what the UI offers, but the dataclass default is an absolute millimetre value so
the math layer never needs to know the model size. ``BrushSettings.with_model_width``
converts the relative default into a concrete radius.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from clayfield.sculpt.falloff import FALLOFFS

ALGORITHMS = ("laplacian", "taubin", "bilateral")

# 15 % of the brush diameter keeps consecutive dabs overlapping enough that a
# fast stroke does not leave scalloped gaps, while staying far enough apart that
# the stroke does not re-smooth the same cells dozens of times per millimetre.
DEFAULT_SPACING_FRACTION = 0.15


@dataclass(frozen=True)
class BrushSettings:
    """Immutable brush configuration.

    ``strength`` is a fraction in ``[0, 1]``; ``radius_mm`` and ``spacing_mm`` are
    physical millimetres. ``spacing_mm`` is the centre-to-centre distance between
    dabs along a stroke; ``None`` selects ``15 %`` of the brush diameter.
    """

    radius_mm: float = 5.0
    strength: float = 0.35
    falloff: str = "smoothstep"
    algorithm: str = "laplacian"
    spacing_mm: float | None = None
    bilateral_spatial: float = 1.0
    bilateral_range_mm: float = 0.25

    def validate(self) -> None:
        """Raise ``ValueError`` for a setting that cannot produce a valid dab."""
        if not math.isfinite(self.radius_mm) or self.radius_mm <= 0.0:
            raise ValueError("Brush radius must be finite and greater than zero")
        if not math.isfinite(self.strength) or not 0.0 <= self.strength <= 1.0:
            raise ValueError("Brush strength must be between 0 and 1")
        if self.falloff not in FALLOFFS:
            raise ValueError(f"Unknown falloff {self.falloff!r}; expected one of {', '.join(FALLOFFS)}")
        if self.algorithm not in ALGORITHMS:
            raise ValueError(f"Unknown algorithm {self.algorithm!r}; expected one of {', '.join(ALGORITHMS)}")
        if self.spacing_mm is not None and (not math.isfinite(self.spacing_mm) or self.spacing_mm <= 0.0):
            raise ValueError("Brush spacing must be finite and greater than zero")
        if not math.isfinite(self.bilateral_spatial) or self.bilateral_spatial <= 0.0:
            raise ValueError("Bilateral spatial sigma must be finite and greater than zero")
        if not math.isfinite(self.bilateral_range_mm) or self.bilateral_range_mm <= 0.0:
            raise ValueError("Bilateral range sigma must be finite and greater than zero")

    @property
    def diameter_mm(self) -> float:
        """Full brush width in millimetres."""
        return 2.0 * self.radius_mm

    @property
    def spacing(self) -> float:
        """Resolved centre-to-centre dab spacing in millimetres."""
        if self.spacing_mm is not None:
            return self.spacing_mm
        return DEFAULT_SPACING_FRACTION * self.diameter_mm

    def with_model_width(self, model_width_mm: float, fraction: float = 0.05) -> BrushSettings:
        """Return a copy whose radius is ``fraction`` of the model width."""
        if not math.isfinite(model_width_mm) or model_width_mm <= 0.0:
            raise ValueError("Model width must be finite and greater than zero")
        return BrushSettings(
            radius_mm=model_width_mm * fraction,
            strength=self.strength,
            falloff=self.falloff,
            algorithm=self.algorithm,
            spacing_mm=self.spacing_mm,
            bilateral_spatial=self.bilateral_spatial,
            bilateral_range_mm=self.bilateral_range_mm,
        )
