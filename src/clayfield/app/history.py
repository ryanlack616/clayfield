"""Bounded parameter history; source pixels are never copied into history."""

from copy import deepcopy
from time import monotonic

from clayfield.app.project_state import ProjectState

PARAMETERS = (
    "source_type", "source_descriptor", "pipeline_snapshot", "secondary_source_descriptor", "mask_source_descriptor", "composition_settings", "secondary_processing_settings", "secondary_field_name", "mask_field_name",
    "inverted", "terrain_width_mm", "terrain_depth_mm", "minimum_height_mm",
    "maximum_height_mm", "heightfield_resolution", "export_resolution", "fabrication_profile", "container_mode", "container_wall_thickness_mm", "container_clearance_mm", "container_outside_dimensions",
    "base_thickness_mm", "relief_mode", "smoothing_sigma", "edge_falloff",
    "edge_falloff_mode", "height_mapping_gamma", "lock_aspect_ratio",
    "noise_amplitude", "noise_frequency", "noise_seed", "adjustment_settings",
    "curve_points", "mapping_curve_points",
    "crop_margins", "image_resize", "height_invert", "height_normalize",
    "height_offset_mm", "height_scale", "height_clamp_min", "height_clamp_max",
    "smoothing_strength", "edge_falloff_strength", "noise_octaves", "noise_persistence",
)


def capture_parameters(state: ProjectState) -> dict:
    return {name: deepcopy(getattr(state, name)) for name in PARAMETERS}


def restore_parameters(state: ProjectState, snapshot: dict) -> None:
    for name in PARAMETERS:
        if name in snapshot:
            setattr(state, name, deepcopy(snapshot[name]))


def _changed_keys(before: dict, after: dict) -> tuple[str, ...]:
    keys = []
    for name in PARAMETERS:
        if name == "adjustment_settings":
            old, new = before[name], after[name]
            keys.extend(f"adjustments.{key}" for key in sorted(old.keys() | new.keys()) if old.get(key) != new.get(key))
        elif before[name] != after[name]:
            keys.append(name)
    return tuple(keys)


class ParameterHistory:
    """Keep parameter snapshots and merge rapid changes to the same controls."""

    def __init__(self, state: ProjectState, limit: int = 100) -> None:
        self.limit = limit
        self.reset(state, clean=True)

    def reset(self, state: ProjectState, *, clean: bool) -> None:
        snapshot = capture_parameters(state)
        self.entries = [snapshot]
        self.index = 0
        self.clean = deepcopy(snapshot) if clean else None
        self._last_key = ()
        self._last_time = 0.0

    def mark_clean(self) -> None:
        self.clean = deepcopy(self.entries[self.index])
        self._last_key = ()

    def finish_group(self) -> None:
        """Keep the next explicit operation separate from recent slider edits."""
        self._last_key = ()

    @property
    def is_dirty(self) -> bool:
        return self.clean is None or self.entries[self.index] != self.clean

    def record(self, state: ProjectState) -> bool:
        snapshot = capture_parameters(state)
        previous = self.entries[self.index]
        key = _changed_keys(previous, snapshot)
        if not key:
            return False
        now = monotonic()
        merge = bool(self._last_key == key and now - self._last_time < 0.6 and self.index == len(self.entries) - 1 and previous != self.clean)
        if merge:
            self.entries[self.index] = snapshot
        else:
            del self.entries[self.index + 1:]
            self.entries.append(snapshot)
            if len(self.entries) > self.limit:
                self.entries.pop(0)
            self.index = len(self.entries) - 1
        self._last_key, self._last_time = key, now
        return True

    def undo(self) -> dict | None:
        if self.index == 0:
            return None
        self.index -= 1
        self._last_key = ()
        return deepcopy(self.entries[self.index])

    def redo(self) -> dict | None:
        if self.index + 1 >= len(self.entries):
            return None
        self.index += 1
        self._last_key = ()
        return deepcopy(self.entries[self.index])
