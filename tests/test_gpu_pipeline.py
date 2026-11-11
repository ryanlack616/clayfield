"""Optional real-context GPU tests plus CPU fallback policy tests."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from clayfield.ui.gpu_pipeline import supports_gpu_adjustments


def test_gpu_preview_supports_filters_and_rejects_invalid_levels():
    assert supports_gpu_adjustments({})
    assert supports_gpu_adjustments({"Blur": 1.0})
    assert supports_gpu_adjustments({"Sharpen": 1.0})
    assert not supports_gpu_adjustments({"Blur": 21.0})
    assert not supports_gpu_adjustments({"Black point": 0.9, "White point": 0.8})


def test_gpu_adjustments_match_cpu_reference():
    if os.environ.get("CLAYFIELD_TEST_GL") != "1":
        pytest.skip("Set CLAYFIELD_TEST_GL=1 with a working desktop OpenGL context")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("gpu_probe.py"))],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_viewport_renders_a_visible_terrain():
    if os.environ.get("CLAYFIELD_TEST_GL") != "1":
        pytest.skip("Set CLAYFIELD_TEST_GL=1 with a working desktop OpenGL context")
    environment = dict(os.environ)
    root = Path(__file__).resolve().parents[1]
    environment["PYTHONPATH"] = str(root / "src")
    result = subprocess.run(
        [sys.executable, str(root / "main.py"), "--gl-self-test"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_gpu_preview_is_replaced_by_cpu_result():
    if os.environ.get("CLAYFIELD_TEST_GL") != "1":
        pytest.skip("Set CLAYFIELD_TEST_GL=1 with a working desktop OpenGL context")
    environment = dict(os.environ)
    root = Path(__file__).resolve().parents[1]
    environment["PYTHONPATH"] = str(root / "src")
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("gpu_preview_probe.py"))],
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
