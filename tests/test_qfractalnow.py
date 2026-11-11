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


def test_chatty_renderer_does_not_deadlock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A renderer that fills the stdout pipe must still complete.

    The old poll()-only loop blocked once the child wrote more than the ~64 KiB
    pipe buffer. This script writes ~160 KiB before producing its PPM.
    """
    script = tmp_path / "fake-fractalnow"
    script.write_text(
        "#!/bin/sh\n"
        "i=0\n"
        "while [ $i -lt 2000 ]; do\n"
        "  printf 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\\n'\n"
        "  i=$((i+1))\n"
        "done\n"
        "out=''\n"
        "prev=''\n"
        "for arg in \"$@\"; do\n"
        "  if [ \"$prev\" = '-o' ]; then out=\"$arg\"; fi\n"
        "  prev=\"$arg\"\n"
        "done\n"
        "printf 'P6\\n24 16\\n255\\n' > \"$out\"\n"
        "head -c 1152 /dev/zero >> \"$out\"\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    monkeypatch.setattr("clayfield.field.qfractalnow.shutil.which", lambda _name: str(script))

    field = render_qfractalnow_config("mandelbrot", (16, 24))

    assert field.values.shape == (16, 24)
    assert field.values.min() >= 0.0
    assert field.values.max() <= 1.0
