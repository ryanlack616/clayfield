# ClayField

ClayField is a PySide6 desktop application for turning images, procedural fields,
and QFractalNow configurations into physical relief models for fabrication.
It provides a live OpenGL viewport, physically meaningful millimeter controls,
validated STL/3MF export, heightmap export, and portable `.clayfield` projects.

## Highlights

- Image, deterministic procedural, and QFractalNow `.config` sources
- Background processing with cancellation and CPU-authoritative export results
- Levels, curves, brightness, contrast, blur, sharpen, threshold, and inversion
- Procedural composition with source-specific secondary-field controls and masks
- Physical dimensions, base thickness, relief mode, and optional container walls
- Floating canvas preview and compose controls with a camera-aware XYZ gizmo
- Surface-aware sculpt brush with Laplacian, Taubin, and bilateral smoothing
- STL, 3MF, PNG, and TIFF export with validation and safety checks
- Portable projects with embedded source images and QFractalNow configs
- Optional GPU preview; CPU processing and export do not require a GPU

## Requirements

- Python 3.12 or newer
- OpenGL 3.3 Core-capable desktop for the live viewport
- Python dependencies declared in `pyproject.toml`
- Optional: `fractalnow` from FractalNow for `.config` sources

## Install and Run

```sh
python -m venv .venv
.venv/bin/python -m pip install -e '.[test,bundle]'
.venv/bin/clayfield
```

On Linux systems with desktop-theme conflicts:

```sh
QT_STYLE_OVERRIDE=Fusion QT_QPA_PLATFORM=xcb .venv/bin/clayfield
```

## Basic Workflow

1. Choose a primary source in the left panel.
2. Load an image, choose a procedural generator, or choose `QFractalNow config` and load a `.config` file.
3. Configure the source-specific controls.
4. Use `COMPOSE` at the bottom of the left panel for a secondary field or mask.
5. Use `PROCESS` for preview selection, curves, levels, and image adjustments.
6. Set physical dimensions and fabrication settings in the right panel.
7. Optionally switch the sculpt panel to `On` and drag over the surface to smooth it.
8. Inspect the viewport and export STL, 3MF, or a heightmap.

QFractalNow configs are embedded into the ClayField project. ClayField invokes
the headless `fractalnow` renderer at the selected preview or export resolution.
The command must be available on `PATH` when opening or regenerating that source.

## Resolution Guidance

For a `250 × 250 mm` relief:

| Resolution | Approximate sample spacing | Typical use |
| --- | ---: | --- |
| 1024 × 1024 | 0.244 mm | General 0.4 mm-nozzle FDM |
| 2048 × 2048 | 0.122 mm | Fine FDM or resin detail |
| 4096 × 4096 | 0.061 mm | High-detail resin, high memory cost |

ClayField defaults to `2048 × 2048`. Procedural sources follow the physical
width/depth ratio, so a `250 × 200 mm` model uses approximately `2048 × 1638`
samples instead of stretching a square field.

## Sculpting

The sculpt panel sits in the bottom-left corner of the viewport. Switch its brush
from `Off` to `On` to route left-drag to the smoothing brush instead of the
camera; middle-drag still pans and the wheel still zooms. The ring under the
pointer is drawn in world space, so it shows the real brush radius on the surface
you are about to edit.

- `Radius` is in millimetres and defaults to a small fraction of the model width.
- `Strength` scales the influence of each dab from 0 to 1.
- `Falloff` selects linear, smoothstep, gaussian, or constant influence.
- `Algorithm` selects Laplacian, Taubin, or bilateral smoothing.

Dabs are spaced along the pointer path by arc length, so a fast stroke applies the
same total influence as a slow one. Each press-drag-release sequence is one undo
step; the Edit menu walks parameter edits and sculpt strokes in the order you made
them. Sculpt work is stored as a displacement layer over the procedural base and
is saved inside the `.clayfield` project, so changing a terrain parameter keeps the
sculpt and reloading a project restores it. A resolution change cannot be mapped
onto the new grid, so the layer is discarded and the status bar says so.

## Tests

```sh
# Either form works; pyproject.toml already sets pythonpath = ["src"], so the
# PYTHONPATH prefix is only needed when invoking a pytest outside the project.
.venv/bin/pytest -q
# or, with uv and the test extra installed in the project environment:
uv run --extra test python -m pytest -q
```

Optional checks:

```sh
CLAYFIELD_STRESS=1 .venv/bin/pytest -q tests/test_stress.py
QT_STYLE_OVERRIDE=Fusion QT_QPA_PLATFORM=xcb CLAYFIELD_TEST_GL=1 .venv/bin/pytest -q tests/test_gpu_pipeline.py
CLAYFIELD_PRUSA_SLICER=/path/to/prusa-slicer .venv/bin/pytest -q tests/test_slicer_integration.py
```

## Linting and formatting

```sh
.venv/bin/pip install -e '.[dev,test]'
.venv/bin/ruff check .          # lint; expected to report no findings
.venv/bin/ruff format --check . # format check without rewriting files
```

With uv: `uv run --extra dev ruff check .`. Configuration is in `pyproject.toml`
(`line-length = 120`, rules `E`, `F`, `I`, `UP`, `B`).

## Build A Linux Bundle

```sh
.venv/bin/python -m PyInstaller --noconfirm --distpath dist/2.0.0 clayfield.spec
dist/2.0.0/clayfield/clayfield --self-test
tar -C dist/2.0.0 -czf dist/clayfield-2.0.0-linux-x86_64.tar.gz clayfield
```

For a source archive:

```sh
git archive --format=tar.gz --prefix=clayfield-2.0.0/ HEAD \
  -o dist/clayfield-2.0.0-source.tar.gz
```

## Project Layout

- `src/clayfield/core`: shared leaf primitives with no Qt/image/mesh dependencies
- `src/clayfield/app`: application lifecycle, state, persistence, and workers
- `src/clayfield/field`: normalized fields, procedural sources, composition
- `src/clayfield/image`: loading, grayscale conversion, curves, and processing
- `src/clayfield/terrain`: physical mapping and fabrication analysis
- `src/clayfield/sculpt`: brush falloffs, surface picking, smoothing kernels, stroke history
- `src/clayfield/geometry`: solid mesh and container generation
- `src/clayfield/export`: STL, 3MF, heightmap output, and verification
- `src/clayfield/ui`: Qt panels, viewport, camera, overlays, and controls
- `designer/image_panel.ui`: editable Qt Designer layout reference
- `tests`: unit, UI, export, persistence, and integration tests
- `docs`: user, development, and print-validation documentation

## License

See [LICENSE](LICENSE).
