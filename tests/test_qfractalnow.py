"""Tests for the embedded QFractalNow source renderer."""

from pathlib import Path
import shutil

import pytest

from clayfield.field.persistence import SourceDescriptor
from clayfield.field.qfractalnow import render_qfractalnow_config


CONFIG = Path("/usr/share/fractalnow/examples/config_files/config01.config")


def test_qfractalnow_descriptor_accepts_embedded_config() -> None:
    descriptor = SourceDescriptor(
        "qfractalnow_config",
        parameters={"filename": "example.config", "config_text": "mandelbrot"},
        algorithm="fractalnow",
        algorithm_version="1",
    )
    assert descriptor.to_dict()["type"] == "qfractalnow_config"


@pytest.mark.skipif(shutil.which("fractalnow") is None or not CONFIG.is_file(), reason="FractalNow is not installed")
def test_qfractalnow_config_renders_to_normalized_field() -> None:
    field = render_qfractalnow_config(CONFIG.read_text(encoding="utf-8"), (16, 24))
    assert field.values.shape == (16, 24)
    assert field.values.min() >= 0.0
    assert field.values.max() <= 1.0
