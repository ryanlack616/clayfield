"""Radial falloff curves for the sculpting brush.

Every curve maps a normalized radius ``t = distance / radius`` to an influence in
``[0, 1]`` and is exactly zero at and beyond ``t = 1``. The brush multiplies the
curve by its strength, so these functions stay independent of brush settings.
"""

from __future__ import annotations

import numpy as np

FALLOFFS = ("linear", "smoothstep", "gaussian", "constant")

# The Gaussian is truncated at t = 1 to keep the brush footprint finite. The
# scale factor 3 puts the cutoff at roughly 3 sigma, so the curve is already
# near zero before the hard edge and the edge does not show as a ring.
_GAUSSIAN_SCALE = 3.0


def falloff_weight(t: np.ndarray | float, kind: str = "smoothstep") -> np.ndarray:
    """Return the falloff influence for normalized radius ``t``.

    ``t`` may be any shape; the result has the same shape. Values below zero are
    treated as the brush centre and values at or above one as outside the brush.
    """
    if kind not in FALLOFFS:
        raise ValueError(f"Unknown falloff {kind!r}; expected one of {', '.join(FALLOFFS)}")
    radius = np.asarray(t, dtype=np.float64)
    if kind == "linear":
        weight = 1.0 - radius
    elif kind == "smoothstep":
        weight = 1.0 - 3.0 * radius**2 + 2.0 * radius**3
    elif kind == "gaussian":
        weight = np.exp(-_GAUSSIAN_SCALE * radius**2)
    else:
        weight = np.ones_like(radius)
    weight = np.where(radius >= 1.0, 0.0, weight)
    weight = np.where(radius < 0.0, 1.0, weight)
    return np.clip(weight, 0.0, 1.0)
