"""Presets retain parameters, not source pixels, and reject invalid files."""

import json
from pathlib import Path

import numpy as np
import pytest

from clayfield.app.history import restore_parameters
from clayfield.app.presets import PresetError, load_preset, save_preset
from clayfield.app.project_state import ProjectState


def test_preset_round_trip_without_source_pixels(tmp_path: Path):
    state = ProjectState(source_image=np.zeros((2, 2), dtype=np.uint8), source_path=tmp_path / "source.png")
    state.crop_margins = (10, 0, 20, 0)
    state.height_offset_mm = 2.5
    state.noise_octaves = 3
    state.adjustment_settings = {"Brightness": 0.2}
    output = save_preset(state, tmp_path / "preset")
    data = json.loads(output.read_text())
    assert "source_image" not in data["parameters"]
    target = ProjectState()
    restore_parameters(target, load_preset(output, target))
    assert target.crop_margins == (10, 0, 20, 0)
    assert target.height_offset_mm == 2.5 and target.noise_octaves == 3
    assert target.adjustment_settings["Brightness"] == 0.2


def test_bad_preset_is_rejected_without_changing_project(tmp_path: Path):
    state = ProjectState(terrain_width_mm=75)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"version": 1, "parameters": {"crop_margins": [80, 0, 80, 0]}}))
    with pytest.raises(PresetError):
        load_preset(path, state)
    assert state.terrain_width_mm == 75
