"""Non-destructive source crop and resize operations."""

import cv2
import numpy as np


def validate_geometry(margins, resize) -> None:
    if not isinstance(margins, (tuple, list)) or len(margins) != 4:
        raise ValueError("Crop margins must contain left, top, right, and bottom percentages")
    if any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 99 for v in margins):
        raise ValueError("Crop margins must be integer percentages from 0 to 99")
    left, top, right, bottom = margins
    if left + right >= 100 or top + bottom >= 100:
        raise ValueError("Crop margins must leave a non-empty image")
    if resize is not None:
        if not isinstance(resize, (tuple, list)) or len(resize) != 2 or any(isinstance(v, bool) or not isinstance(v, int) or not 2 <= v <= 8192 for v in resize):
            raise ValueError("Resize dimensions must be integers from 2 to 8192 pixels")


def crop_bounds(width: int, height: int, margins) -> tuple[int, int, int, int]:
    validate_geometry(margins, None)
    left, top, right, bottom = margins
    x0 = min(width - 1, round(width * left / 100))
    y0 = min(height - 1, round(height * top / 100))
    x1 = max(x0 + 1, width - round(width * right / 100))
    y1 = max(y0 + 1, height - round(height * bottom / 100))
    return x0, y0, x1, y1


def processed_dimensions(width: int, height: int, margins, resize) -> tuple[int, int]:
    validate_geometry(margins, resize)
    if resize is not None:
        return tuple(resize)
    if width < 1 or height < 1:
        return 0, 0
    x0, y0, x1, y1 = crop_bounds(width, height, margins)
    return x1 - x0, y1 - y0


def apply_image_geometry(source: np.ndarray, margins=(0, 0, 0, 0), resize=None) -> np.ndarray:
    """Return a cropped/resized view or array without modifying source pixels."""
    validate_geometry(margins, resize)
    height, width = source.shape[:2]
    x0, y0, x1, y1 = crop_bounds(width, height, margins)
    result = source[y0:y1, x0:x1]
    if resize is not None and (result.shape[1], result.shape[0]) != tuple(resize):
        interpolation = cv2.INTER_AREA if resize[0] <= result.shape[1] and resize[1] <= result.shape[0] else cv2.INTER_LINEAR
        result = cv2.resize(result, tuple(resize), interpolation=interpolation)
    return result
