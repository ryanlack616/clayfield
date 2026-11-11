"""Exercise the GPU preview and authoritative CPU replacement in a real window."""

import sys
import time
import traceback
from pathlib import Path

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import clayfield.ui.image_panel as image_panel
import clayfield.ui.main_window as main_window
from clayfield.app.application import configure_opengl
from clayfield.ui.gpu_pipeline import GpuImagePipeline

configure_opengl()
app = QApplication([])
main_window.find_recovery_snapshots = lambda: []
window = main_window.MainWindow()
window.state.set_source(Path("probe.png"), np.tile(np.arange(128, dtype=np.uint8), (128, 1)))
window.image_panel.refresh_from_state()
window.show()
events = []
gpu_process = GpuImagePipeline.process


def assert_no_readback(self, *args, **kwargs):
    assert kwargs.get("readback") is False
    return gpu_process(self, *args, **kwargs)


GpuImagePipeline.process = assert_no_readback
window.viewport.gpu_adjustments_ready.connect(lambda generation, result: events.append(generation))
stage = 0
started = time.monotonic()


def poll():
    global stage
    try:
        if stage == 0 and window.state.physical_heightfield is not None:
            original = image_panel._process_adjustments

            def slow_cpu(*args, **kwargs):
                time.sleep(0.5)
                return original(*args, **kwargs)

            image_panel._process_adjustments = slow_cpu
            window.image_panel.controls["Blur"].setValue(1.0)
            window.image_panel.controls["Brightness"].setValue(0.1)
            stage = 1
        elif stage == 1 and window.state.physical_heightfield is not None:
            assert events, "GPU preview was not emitted before the CPU result"
            assert window.viewport.gpu_adjustments_enabled
            window.viewport.set_grid_visible(False)
            window.viewport.set_orthographic(True)
            assert not window.viewport.grabFramebuffer().isNull()
            assert window.viewport.orthographic and not window.viewport.show_grid
            print("GPU preview and CPU replacement completed", flush=True)
            window.state.dirty = False
            app.exit(0)
        if time.monotonic() - started > 8:
            raise TimeoutError("Preview processing timed out")
    except Exception:
        traceback.print_exc()
        window.state.dirty = False
        app.exit(1)


timer = QTimer()
timer.timeout.connect(poll)
timer.start(20)
sys.exit(app.exec())
