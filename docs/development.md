# Development and release

Install Python 3.12 or newer and run:

```sh
python -m venv .venv
.venv/bin/pip install -e '.[test,bundle]'
.venv/bin/pytest -q
```

`pyproject.toml` sets `pythonpath = ["src"]`, so a separate `PYTHONPATH` prefix
is only needed when invoking a pytest outside the project. With uv, use
`uv run --extra test python -m pytest -q` so the project environment (and its
test extra) is used.

## Linting and formatting

`ruff` is the lint and format gate, installed by the `dev` extra:

```sh
.venv/bin/pip install -e '.[dev,test]'
.venv/bin/ruff check .          # lint; expected to report no findings
.venv/bin/ruff format --check . # format check without rewriting files
.venv/bin/ruff format .         # apply formatting
```

With uv, use `uv run --extra dev ruff check .` and
`uv run --extra dev ruff format .`. Configuration lives in `pyproject.toml`:
`line-length = 120`, rules `E`, `F`, `I`, `UP`, `B`, with `E501` ignored because
the codebase deliberately uses long explanatory comments and docstrings. The two
PyOpenGL modules are exempt from `F403`/`F405` because the library's public API
is conventionally star-imported.

The normal tests use Qt's offscreen platform and skip integration tests that
need external programs or a real OpenGL context. To run the additional checks:

```sh
CLAYFIELD_STRESS=1 .venv/bin/pytest -q tests/test_stress.py
QT_STYLE_OVERRIDE=Fusion QT_QPA_PLATFORM=xcb CLAYFIELD_TEST_GL=1 .venv/bin/pytest -q tests/test_gpu_pipeline.py
CLAYFIELD_PRUSA_SLICER=/path/to/prusa-slicer .venv/bin/pytest -q tests/test_slicer_integration.py
```

The GPU test compares supported tonal operations with the CPU reference at an
absolute tolerance of 0.001, including blur and sharpening. The slicer test checks both STL and 3MF dimensions,
manifoldness, and successful G-code generation. `clayfield --self-test` checks
packaged resources and mesh generation; `clayfield --gl-self-test` additionally
renders a terrain in a desktop OpenGL context.

## V2 pre-release checks

Before V2 release work is considered complete:

1. Validate the V1 archive contents with a 7-Zip-compatible tool and retain its
   SHA-256 checksum and restore procedure.
2. Run the V1 baseline and current full test suite in a clean virtual
   environment.
3. Verify image-primary and procedural-primary composition produce equivalent
   field, mapping, fabrication, and export semantics.
4. Verify complete external artifacts, hashes, and
   normalized working fields survive project save/load according to the chosen
   artifact policy.
5. Verify the final export-resolution fabrication metrics are shown before
   export confirmation.
6. Verify cancellation during generator, processing, analysis, mesh,
   and file-writing stages.
7. Run STL/3MF slicer checks for native, composed, and imported
   representative projects.
8. Verify fresh wheel, bundle, packaged self-test, and OpenGL self-test paths.

The authoritative task status and release blockers are maintained in
[`V2-MASTER-PLAN.md`](../V2-MASTER-PLAN.md), Sections 21 and 22.
The concise daily execution board is
[`V2-MASTER-TASK-LIST.md`](../V2-MASTER-TASK-LIST.md).
The single completion roadmap is
[`V2-CANONICAL-ROADMAP.md`](../V2-CANONICAL-ROADMAP.md).
The V1 rollback procedure is in [`v1_restore.md`](v1_restore.md).

## Sculpting subsystem

`src/clayfield/sculpt/` holds the interactive mesh-editing foundation. ClayField
does not keep a triangle mesh in the interactive path: `generate_solid_mesh`
builds the closed solid on demand for STL/3MF export. The authoritative geometry
is the CPU heightfield, so the brush paints a displacement into that grid and
export still reads one surface.

Coordinate convention, shared with the viewport and `terrain/heightfield.py`:

- `heightfield[row, column]` is millimetres above the base plane.
- `row` increases with `+z`; `column` increases with `+x`.
- `x` spans `[-width_mm / 2, +width_mm / 2]`, `z` spans `[-depth_mm / 2, +depth_mm / 2]`.
- The viewport renders in `mm / 20` units, so a ray produced in viewport units
  must have its origin scaled by 20 before intersecting a heightfield in mm.

Module responsibilities:

| Module | Responsibility |
| --- | --- |
| `brush.py` | Validated brush settings and falloff/algorithm names |
| `falloff.py` | Linear, smoothstep, gaussian, constant influence curves |
| `brush_query.py` | Rectangular footprint with zero-weight stencil margin |
| `stroke.py` | Arc-length dab spacing between pointer samples |
| `surface_picking.py` | Screen ray, heightfield intersection, bilinear sampling |
| `smooth_laplacian.py` | Four-neighbour Laplacian kernel |
| `smooth_taubin.py` | Alternating lambda/mu passes |
| `smooth_bilateral.py` | Distance and height-difference weighted average |
| `session.py` | One press-drag-release stroke over the heightfield and layer |
| `history.py` | Bounded stroke stack and in-place before/after restore |

Two design points are worth keeping in mind when extending this.

*The smoothing kernels are grid specializations, not mesh operators.* The handoff
specification describes cotangent-weighted Laplacian smoothing for irregular
triangle meshes. ClayField's interactive surface is a regular grid, where the
cotangent weights collapse to a constant four-neighbour stencil. The kernels are
written against that stencil; the interfaces take a block plus per-cell weights,
so a triangle-mesh backend can replace them without changing `session.py`.

*The sculpt layer is a displacement, not a replacement.* `state.sculpt_base` holds
the evaluated procedural field and `state.sculpt_offsets` holds the per-cell
displacement, with `state.physical_heightfield == sculpt_base + sculpt_offsets`
whenever a layer exists. `_apply_sculpt_layer` reapplies the layer when the base is
regenerated and discards it when the grid shape changes. `EditLedger` in
`app/history.py` orders parameter snapshots and sculpt strokes so mixed undo and
redo follow the order the user made them.

## Numerical compatibility policy

Same-stack deterministic generators should match reference fixtures within
`2e-5` absolute field tolerance. CPU/GPU preview agreement uses the existing
`0.001` absolute tolerance. Physical bounds and exported dimensions must match
within `1e-4` mm where the format and floating-point path allow it.

Supported development targets begin at Python 3.12 with the dependency ranges
declared in `pyproject.toml`. A dependency upgrade that changes field samples,
mapping results, or mesh dimensions requires refreshed fixtures and a documented
compatibility decision.

Current local hardening observations:

- The current suite passes `250 passed, 7 skipped`.
- `clayfield --self-test` passes.
- A wheel builds successfully and installs/imports in a clean temporary Python
  environment.
- Full 1024 x 1024 mesh validation can peak around 3.5 GiB on this host. The
  exporter uses a measured 7x working-set factor; 1024² and 4096² exports fit
  the default budget, and 8192² is rejected.
- No live ComfyUI endpoint, PrusaSlicer executable, 7-Zip-compatible command,
  additional GPU/OS target, or physical printer is configured in this
  environment.

Run `.venv/bin/python benchmarks/benchmark_pipeline.py` for local image and mesh
timings and peak RSS. On the Ubuntu 26.04 development host with Python 3.12,
a 2048² image took 0.028 s cold and 0.003 s for a cached blur-only edit; a
1024² mesh was quick to construct but full validation can peak substantially
above the persistent mesh arrays. These are observations, not performance
guarantees, and should be treated as safety limits rather than promises.

Generate deterministic V2 sample projects and artifacts with:

```sh
.venv/bin/python benchmarks/v2_samples.py --output dist/v2-samples --size 128
```

The sample generator writes noise, wave, and Mandelbrot `.clayfield` projects,
STL files, and PNG heightmaps.

Generate fabrication calibration panels with:

```sh
.venv/bin/python benchmarks/fabrication_calibration.py --output dist/fabrication-calibration --size 256
```

The calibration generator writes STL and 3MF panels for feature width, slope,
and recessed wall-depth inspection. These digital artifacts still require a
physical print before fabrication-profile limits can be considered validated.

## Linux bundle

Build on a Linux system compatible with the intended target systems:

```sh
.venv/bin/python -m PyInstaller --noconfirm --distpath dist/2.0.0 clayfield.spec
dist/2.0.0/clayfield/clayfield --self-test
dist/2.0.0/clayfield/clayfield --gl-self-test
tar -C dist/2.0.0 -czf dist/clayfield-2.0.0-linux-x86_64.tar.gz clayfield
```

The resulting directory contains the application and its bundled libraries.
It still requires a working desktop and a host OpenGL driver. PyInstaller
bundles are built for the build machine's architecture and libc baseline.

## Release Process

Update the version in `pyproject.toml` and `src/clayfield/__init__.py`, add
release notes to `CHANGELOG.md`, run the full test suite, build a fresh wheel,
and run the PyInstaller self-test before publishing a release.

For a source archive from the repository root:

```sh
git archive --format=tar.gz --prefix=clayfield-2.0.0/ HEAD \
  -o dist/clayfield-2.0.0-source.tar.gz
```

For a Linux application bundle, use the commands in the Linux bundle section.
Do not include `.venv`, `build`, `dist`, credentials, or local project files in
source commits.
