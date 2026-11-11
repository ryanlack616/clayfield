"""Portable, source-free image and terrain parameter presets."""

import json
import os
import tempfile
from copy import copy
from pathlib import Path

import numpy as np

from clayfield.app.history import PARAMETERS, capture_parameters, restore_parameters
from clayfield.app.project_io import ProjectIOError, _parse_curve_points
from clayfield.image.geometry import validate_geometry
from clayfield.image.levels import apply_levels
from clayfield.terrain.heightfield import PhysicalDimensions, options_from_state


class PresetError(ValueError):
    """Raised when a preset cannot be read or validated."""


def save_preset(state, path) -> Path:
    output = Path(path).expanduser()
    if output.suffix.lower() != ".json":
        output = output.with_suffix(".json")
    temporary = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
        temporary = Path(name)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump({"version": 1, "parameters": capture_parameters(state)}, file, indent=2, allow_nan=False)
        temporary.replace(output)
        return output
    except (OSError, TypeError, ValueError) as error:
        raise PresetError(f"Could not save preset: {error}") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_preset(path, state) -> dict:
    """Return a validated parameter snapshot without modifying the project."""
    try:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("parameters"), dict):
            raise PresetError("Invalid or unsupported preset")
        supplied = data["parameters"]
        if set(supplied) - set(PARAMETERS):
            raise PresetError("Preset contains unknown parameters")
        snapshot = capture_parameters(state)
        snapshot.update(supplied)
        for name in ("curve_points", "mapping_curve_points"):
            snapshot[name] = _parse_curve_points(snapshot[name], name)
        for name in ("heightfield_resolution", "export_resolution", "image_resize", "crop_margins"):
            if snapshot[name] is not None:
                snapshot[name] = tuple(snapshot[name])
        validate_geometry(snapshot["crop_margins"], snapshot["image_resize"])
        for name, maximum in (("heightfield_resolution", 2048), ("export_resolution", 4096)):
            resolution = snapshot[name]
            if resolution is not None and (len(resolution) != 2 or any(isinstance(v, bool) or not isinstance(v, int) or not 2 <= v <= maximum for v in resolution)):
                raise PresetError(f"Invalid {name}")
        temp = copy(state)
        restore_parameters(temp, snapshot)
        dimensions = PhysicalDimensions(temp.terrain_width_mm, temp.terrain_depth_mm, temp.minimum_height_mm, temp.maximum_height_mm)
        dimensions.validate()
        options_from_state(temp).validate()
        if not (0 < temp.terrain_width_mm <= 10000 and 0 < temp.terrain_depth_mm <= 10000 and
                0 <= temp.minimum_height_mm <= temp.maximum_height_mm <= 10000 and
                abs(temp.height_offset_mm) <= 10000 and temp.height_scale <= 100 and
                0 < temp.base_thickness_mm <= 10000 and 0 <= temp.smoothing_sigma <= 50 and
                0 <= temp.edge_falloff <= 1 and 0.05 <= temp.height_mapping_gamma <= 10 and
                0 <= temp.noise_amplitude <= 1 and 0.1 <= temp.noise_frequency <= 32):
            raise PresetError("Preset contains out-of-range terrain settings")
        if temp.relief_mode not in {"positive", "negative"} or temp.edge_falloff_mode not in {"linear", "smoothstep"}:
            raise PresetError("Preset contains an invalid terrain mode")
        for name in ("inverted", "lock_aspect_ratio", "height_invert", "height_normalize"):
            if not isinstance(snapshot[name], bool):
                raise PresetError(f"Invalid {name}")
        if not isinstance(temp.noise_seed, int) or isinstance(temp.noise_seed, bool) or not -2147483648 <= temp.noise_seed <= 2147483647:
            raise PresetError("Invalid noise seed")
        settings = temp.adjustment_settings
        if not isinstance(settings, dict):
            raise PresetError("Invalid adjustment settings")
        known = {"Black point", "Gamma", "White point", "Output black", "Output white", "Brightness", "Contrast", "Blur", "Sharpen", "Threshold", "threshold_enabled", "linear_light", "Curve interpolation", "inverted"}
        if set(settings) - known:
            raise PresetError("Preset contains unknown adjustment settings")
        apply_levels(np.zeros((1, 1), dtype=np.float32), float(settings.get("Black point", 0)), float(settings.get("Gamma", 1)), float(settings.get("White point", 1)), float(settings.get("Output black", 0)), float(settings.get("Output white", 1)))
        if settings.get("Curve interpolation", "linear") not in {"linear", "smoothstep"}:
            raise PresetError("Invalid curve interpolation")
        ranges = {"Gamma": (0.1, 5), "Brightness": (-1, 1), "Contrast": (0, 4), "Blur": (0, 20), "Sharpen": (0, 5), "Threshold": (0, 1)}
        for name, (minimum, maximum) in ranges.items():
            value = float(settings.get(name, 1 if name in {"Gamma", "Contrast"} else 0))
            if not np.isfinite(value) or not minimum <= value <= maximum:
                raise PresetError(f"Invalid {name}")
        for name in ("threshold_enabled", "linear_light", "inverted"):
            if name in settings and not isinstance(settings[name], bool):
                raise PresetError(f"Invalid {name}")
        return snapshot
    except PresetError:
        raise
    except (OSError, TypeError, ValueError, KeyError, ProjectIOError) as error:
        raise PresetError(f"Invalid preset: {error}") from error
