"""Taubin (lambda/mu) smoothing on a heightfield block.

Two alternating Laplacian passes with a positive lambda and a negative mu shrink
high-frequency detail while largely cancelling the low-frequency volume loss of a
single repeated Laplacian filter. The default pair ``(0.5, -0.53)`` is the classic
Taubin choice and satisfies ``1/lambda + 1/mu > 0``, the passivity condition that
keeps the filter from amplifying frequencies.

The same brush weights are applied to both passes so the smoothed footprint stays
localized to the dab.
"""

from __future__ import annotations

import numpy as np

from clayfield.sculpt.smooth_laplacian import NEIGHBOURS, laplacian_delta

# The classic pair assumes the neighbour-average form, where one pass multiplies
# the highest-frequency component by ``1 - 2*lambda``. Applied to the raw
# Laplacian (eigenvalue 8) the same numbers multiply it by ``1 - 8*lambda`` and the
# second pass amplifies the first, so both passes divide by the neighbour count.
DEFAULT_LAMBDA = 0.5
DEFAULT_MU = -0.53


def smooth_taubin(
    block: np.ndarray,
    weights: np.ndarray,
    lambda_: float = DEFAULT_LAMBDA,
    mu: float = DEFAULT_MU,
) -> np.ndarray:
    """Return one Taubin pass over ``block`` using the supplied brush weights.

    The input block is not modified. ``weights`` already carries the brush
    strength and falloff.
    """
    values = np.asarray(block, dtype=np.float32)
    influence = np.asarray(weights, dtype=np.float32)
    if values.shape != influence.shape:
        raise ValueError("Taubin weights must match the block shape")
    if not np.isfinite(lambda_) or lambda_ <= 0.0:
        raise ValueError("Taubin lambda must be finite and positive")
    if not np.isfinite(mu) or mu >= 0.0:
        raise ValueError("Taubin mu must be finite and negative")
    # Passivity: 1/lambda + 1/mu > 0 keeps the alternating pair from amplifying a
    # frequency band instead of damping it. The classic (0.5, -0.53) satisfies it
    # and so does any pair scaled by a positive factor.
    if 1.0 / lambda_ + 1.0 / mu <= 0.0:
        raise ValueError("Taubin lambda and mu violate the passivity condition")
    step = influence / NEIGHBOURS
    first = values + float(lambda_) * step * laplacian_delta(values)
    second = first + float(mu) * step * laplacian_delta(first)
    return second.astype(np.float32)
