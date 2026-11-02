"""Pure image-adjustment pipeline suitable for worker execution."""

from __future__ import annotations

import numpy as np
from threading import Lock

from clayfield.app.cancellation import check_cancelled
from clayfield.image.curves import apply_curve
from clayfield.image.filters import adjust_brightness_contrast, gaussian_blur, sharpen, threshold
from clayfield.image.grayscale import invert
from clayfield.image.levels import apply_levels


def apply_adjustments(
    image: np.ndarray,
    settings: dict[str, float | bool],
    curve_points: list[tuple[float, float]],
) -> np.ndarray:
    """Apply all image adjustments without accessing Qt or mutable UI state."""
    get = lambda name, default: float(settings.get(name, default))
    result = invert(image) if bool(settings.get("inverted", False)) else image.copy()
    result = apply_levels(
        result,
        get("Black point", 0.0),
        get("Gamma", 1.0),
        get("White point", 1.0),
        get("Output black", 0.0),
        get("Output white", 1.0),
    )
    result = apply_curve(result, curve_points, str(settings.get("Curve interpolation", "linear")))
    result = adjust_brightness_contrast(result, get("Brightness", 0.0), get("Contrast", 1.0))
    result = gaussian_blur(result, get("Blur", 0.0))
    result = sharpen(result, get("Sharpen", 0.0))
    if bool(settings.get("threshold_enabled", False)):
        result = threshold(result, get("Threshold", 0.5))
    return result.astype(np.float32, copy=False)


class AdjustmentCache:
    """Cache ordered stages for one immutable grayscale source at a time."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._source = None
        self._stages = [None] * 6

    def apply(self, image, settings, curve_points, *, cancel_check=None):
        get = lambda name, default: float(settings.get(name, default))
        level = (bool(settings.get("inverted", False)), get("Black point", 0), get("Gamma", 1),
                 get("White point", 1), get("Output black", 0), get("Output white", 1))
        curve = (tuple(tuple(p) for p in curve_points), str(settings.get("Curve interpolation", "linear")))
        contrast = (get("Brightness", 0), get("Contrast", 1))
        blur = get("Blur", 0)
        sharp = get("Sharpen", 0)
        cutoff = (bool(settings.get("threshold_enabled", False)), get("Threshold", 0.5))
        operations = (
            (level, lambda x: apply_levels(invert(x) if level[0] else x, *level[1:])),
            (curve, lambda x: apply_curve(x, list(curve[0]), curve[1])),
            (contrast, lambda x: adjust_brightness_contrast(x, *contrast)),
            (blur, lambda x: gaussian_blur(x, blur) if blur else x),
            (sharp, lambda x: sharpen(x, sharp) if sharp else x),
            (cutoff, lambda x: threshold(x, cutoff[1]) if cutoff[0] else x),
        )
        with self._lock:
            check_cancelled(cancel_check)
            if self._source is not image:
                self._source = image
                self._stages = [None] * len(operations)
            result = image
            key = ()
            for index, (parameters, operation) in enumerate(operations):
                check_cancelled(cancel_check)
                key = (key, parameters)
                cached = self._stages[index]
                if cached is not None and cached[0] == key:
                    result = cached[1]
                else:
                    result = operation(result)
                    check_cancelled(cancel_check)
                    self._stages[index] = (key, result)
            return result.astype(np.float32, copy=False)
