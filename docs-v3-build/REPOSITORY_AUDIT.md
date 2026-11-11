# Repository Audit — ClayField v3 handoff

- Date: 2026-11-11
- Method: read-only. No source edits, no installs, no config changes. Commands and outputs are verbatim in Appendix A.
- Scope: the Phase 0 checklist in `TASK_LIST.md` and the "first action" in `README.md`.

## Verdict

The application is healthy and runnable: 75 modules import cleanly, the built-in
self-test passes, and 361 tests pass with 0 failures. The v3 package's engineering
principles are compatible with what exists.

But the v3 **UI** is not an evolution of the current window — it is a different
architecture. The current app is a two-pane splitter with a bottom-anchored
viewport overlay. The v3 spec is a docked three-column shell with five workspace
tabs, a persistent viewport, and a painted weighted mask. Neither docks, tabs, nor
a mask editor exist today. Phase 1 is therefore a shell rebuild, not a restyle.

The single largest risk the audit removes: **the mask does not exist as a
first-class editable object.** The state carries a mask array and projects
serialize it, but nothing in the UI creates or edits one. The v3 product's
defining capability has no implementation to preserve.

## Verified facts

### Entry point and launch

| Fact | Value |
|---|---|
| Entry point | `main.py` → `clayfield.app.application:run` |
| Console script | `clayfield = "clayfield.app.application:run"` (pyproject) |
| Headless modes | `--version`, `--self-test`, `--gl-self-test` |
| Version | `ClayField 2.0.0` |
| Self-test | passes (shaders present, mesh generates and validates) |

The headless modes matter for Phase 0 and for CI: version and geometry self-test
run without a display. Only `--gl-self-test` needs an OpenGL context.

### Environment

| Fact | Value |
|---|---|
| `requires-python` | `>=3.12` |
| Project venv | `.venv`, Python 3.13.18 |
| System python | 3.14.9 |
| Lockfile | `uv.lock` present |
| Dependencies | PySide6>=6.6, PyOpenGL>=3.1 (+accelerate), numpy>=2.0, opencv-python>=4.8, Pillow>=10.0, scipy>=1.11, trimesh>=4.0 |
| Test extras | pytest>=8, lib3mf>=2.4 (Linux x86_64), bundle: pyinstaller>=6.11, dev: ruff>=0.6 |

### Size

- `src/` — 14,045 lines across 75 modules.
- `tests/` — 5,053 lines.

### Module map (verified paths)

| Layer | Path | Contents |
|---|---|---|
| App | `src/clayfield/app/` | `application.py`, `project_state.py`, `project_io.py`, `history.py`, `presets.py`, `recovery.py`, `worker.py`, `cancellation.py` |
| Core | `src/clayfield/core/` | `cancellation.py` |
| Image | `src/clayfield/image/` | `loader.py`, `grayscale.py`, `geometry.py`, `levels.py`, `curves.py`, `filters.py`, `pipeline.py` |
| Field | `src/clayfield/field/` | `model.py`, `generators.py`, `processing.py`, `composition.py`, `pipeline.py`, `workflow.py`, `persistence.py`, `contours.py`, `qfractalnow.py` |
| Terrain | `src/clayfield/terrain/` | `heightfield.py`, `mapping.py`, `cross_section.py`, `fabrication.py` |
| Geometry | `src/clayfield/geometry/` | `mesh_generator.py`, `validation.py`, `container.py`, `estimates.py` |
| Sculpt | `src/clayfield/sculpt/` | `brush.py`, `stroke.py`, `session.py`, `history.py`, `falloff.py`, `brush_query.py`, `surface_picking.py`, `smooth_bilateral.py`, `smooth_laplacian.py`, `smooth_taubin.py` |
| Export | `src/clayfield/export/` | `stl.py`, `three_mf.py`, `heightmap.py`, `orientation.py`, `verification.py`, `tasks.py` |
| UI | `src/clayfield/ui/` | `main_window.py`, `viewport.py`, `gpu_pipeline.py`, `image_panel.py`, `sculpt_panel.py`, `terrain_panel.py`, `theme.py`, `camera.py`, `axis_gizmo.py`, `cross_section.py`, `curve_editor.py`, `export_preview.py`, `height_colors.py`, `histogram.py`, `parameter_row.py` |

### Tests

`env -u PYTHONPATH .venv/bin/python -m pytest -q` → **361 passed, 7 skipped in 192.73s**, exit 0.
The 7 skips are GPU/display-dependent; no failures.

### Baseline launch behavior

The GUI launches. The first attempt failed only because `DISPLAY` was unset and
`~/.Xauthority` does not exist; this session's X server is Xwayland on `:0`,
authenticated by `/run/user/1000/.mutter-Xwaylandauth.J78QY3`. The recipe:

```bash
DISPLAY=:0 XAUTHORITY=/run/user/1000/.mutter-Xwaylandauth.J78QY3 \
  env -u PYTHONPATH PYTHONPATH=src .venv/bin/python main.py --gl-self-test
```

`--gl-self-test` prints `OpenGL 3.3.0 NVIDIA 595.99.02; terrain vertices: 6;
changed pixel channels: 427798; GPU error: 0.000000` and exits 0. The GL path is
exercised, not merely documented — the earlier "authorization required" abort was
a missing `XAUTHORITY`, not an application defect.

Constructing and showing the window gives the real baseline:

| Fact | Value |
|---|---|
| Window title | `ClayField — Untitled` |
| Window size | 1309 × 820 |
| Size requested | `resize(1280, 820)` — line 120; minimum size hint is 1309 × 440, so 1280 is not honoured |
| Central widget | `QSplitter` |
| Menu bar | File, Edit, View, Operations |
| Status bar | present |
| Bottom overlay width | 390 |
| GL context | valid, 4.6, compatibility profile, 0 samples |
| Screen | 3440 × 1440, dpr 1.0, 96 dpi |
| Result | constructed OK, exit 0 |

The 1600 × 1000 default the v3 spec asks for clears the 1309 × 440 floor, so the
resize target is not the constraint — the dock layout is.

The offscreen platform cannot create a `QOpenGLWidget` context, so the viewport
has to be exercised on a real display; `--gl-self-test` is the bounded way to do
it.

### Main window

| Fact | Value |
|---|---|
| Class | `MainWindow(QMainWindow)` in `src/clayfield/ui/main_window.py` |
| Default size | `self.resize(1280, 820)` — line 120 |
| Layout | one `QSplitter` — line 150 |
| Dock widgets | **none** (`grep QDockWidget src/` → 0 hits) |
| Tab widget | **none** (`grep QTabWidget|addTab src/` → 0 hits) |
| Bottom overlay | `self.compose_overlay.setFixedWidth(390)` — line 203 |
| Title | `ClayField — <project>` with `*` dirty marker |
| Settings | `QSettings("ClayField", "ClayField")` — line 113 |

### Mask — current implementation

State (`src/clayfield/app/project_state.py`):
- `mask_source_descriptor: dict | None` (line 22)
- `mask_field: np.ndarray | None` (line 29)
- `mask_field_name: str | None` (line 30)
- `mask_original_bytes: bytes | bytearray | None` (line 34)

Persistence (`src/clayfield/app/project_io.py`):
- `mask_field.png` — 16-bit PNG, `np.rint(values * 65535).astype(np.uint16)` (lines 462–473, 565–569)
- `mask_original.bin` — raw original bytes (lines 572–573, 623–635)

Composition (`src/clayfield/field/composition.py`):
- mask must match primary shape; scales replacement per sample: `effective_amount * mask.values` (lines 30–56)

UI (`src/clayfield/ui/image_panel.py`):
- Radial mask only: `mask_enabled`, `mask_radius` (0.01–1.5, default 0.7), `mask_feather` (0–1, default 0.1), `mask_invert` (lines 852–863)
- `Import Mask…` button → `_choose_mask_field()` (line 1009); sets `state.mask_field` / `mask_field_name` (lines 1050–1051)
- Status line reports mask type and embedded/external (lines 334–342)

**Absent:** any mask painting/editing tool. `grep -i "mask" src/clayfield/ui/viewport.py src/clayfield/ui/gpu_pipeline.py` → **0 hits**, so the viewport renders no mask overlay. There is no mask editor class anywhere in `src/`.

### Analysis — current implementation

`analyze_heightfield(...)` in `src/clayfield/terrain/fabrication.py:71` returns
`FabricationMetrics`: resolved feature width, maximum slope, minimum wall,
relief range, base thickness, plus warnings (`insufficient_base_thickness`,
`invalid_heightfield`). This is **printability/fabrication** analysis.

It is not surface-defect analysis at a selected physical scale. The v3 product's
"detect small unwanted irregularities" capability has no implementation.

### Undo/redo

`src/clayfield/app/history.py`:
- `EditLedger` — `record`, `undo`, `redo`, `discard`, `drop_oldest`, `clear`, `index`, `can_undo`, `can_redo`
- `ParameterHistory` — snapshot-based, `limit=100`, dirty tracking via `mark_clean`

### Export

- `export_stl(mesh, path, *, cancel_check=None)` — `src/clayfield/export/stl.py:21`
- `export_3mf(mesh, path, *, cancel_check=None)` — `src/clayfield/export/three_mf.py:18`
- Plus `heightmap.py`, `orientation.py`, `verification.py`, and worker wrappers in `tasks.py`

### Assets

Shaders: `src/clayfield/resources/` — `test_grid.vert/.frag`, `image_process.vert/.frag`,
`image_filter.frag` (declared in `package-data`). A duplicate `shaders/` at the repo
root holds only `test_grid.*`.

## Gap analysis against the v3 spec

| v3 requirement | Current state | Gap |
|---|---|---|
| Main window 1600×1000 | 1309×820 actual (`resize(1280, 820)` is not honoured; min hint 1309×440) | resize constant |
| Left source dock 260px | no dock | **architectural** |
| Right settings dock 360px | no dock; compose overlay 390px fixed | **architectural** |
| Five workspace tabs in right dock | no `QTabWidget` | **architectural** |
| Viewport persistent across tabs | viewport is a splitter pane + overlay | **architectural** |
| Docks resize/move/float/hide/persist | `QSplitter` only; no dock persistence | **architectural** |
| Weighted mask, painted and editable | radial mask + imported array; no editor, no overlay | **capability absent** |
| Mask independent of geometry, retained across cleanup | mask stored in state and serialized; independence partially holds | mostly present |
| Scale-aware surface analysis | fabrication metrics only | **capability absent** |
| Mask-aware selective cleanup | global/sculpt brushes only | **capability absent** |
| Destructive ops previewable/undoable | `EditLedger` + `ParameterHistory` | present |
| Explicit physical units | `mm` throughout terrain/geometry | present |
| STL/3MF export | present | present |
| Settings persistence | `QSettings` | present |

### What is genuinely reusable

- The image → heightfield → mesh → export pipeline is real and tested.
- The mask array and its 16-bit PNG serialization already exist in the document
  format, so the mask *data model* survives into v3.
- `EditLedger`/`ParameterHistory` cover undo for parameter and sculpt edits.
- Physical units are already explicit in the terrain and geometry layers.
- The OpenGL 3.3 core-profile viewport and shader set work.

### What must be rebuilt

- The window shell: docks, tabs, layout persistence, workspace state.
- The mask as an editable object: painting, weighted values, overlay rendering,
  morphology, and the mask↔geometry mapping.
- Surface analysis at a physical scale: local defect detection, not printability.
- Selective cleanup driven by the mask.

## Phase 0 exit-gate questions

The roadmap asks three representation questions. The audit answers them:

1. **Authoritative geometry representation:** heightfield → `SolidMesh` via
   `generate_solid_mesh` (`geometry/mesh_generator.py`), validated by
   `validate_mesh`. The mesh is the export artifact; the heightfield is the
   editable source. Mask should align to the heightfield grid (matching v3's
   "if the application uses a heightfield, align mask samples to the heightfield").
2. **Mask representation:** `NormalizedField`-shaped `np.ndarray`, 0–1, already
   serialized as 16-bit PNG. Reuse this; do not introduce a second mask type.
3. **Undo scope:** `EditLedger` covers parameters and sculpt strokes. Mask edits
   need a new ledger kind; the mechanism already exists.

## Recommendation

Accept the v3 product definition and treat Phase 1 as a shell rebuild. Reuse the
pipeline, the mask data model, the export path, and the undo ledger; build the
dock/tab shell, the mask editor, the scale-aware analyzer, and mask-driven cleanup
as new. Do not attempt to retrofit the v3 layout onto the current splitter.

The direction conflict this audit surfaced is now decided: ADR-0002 makes desktop
V3 the active product and the web builds a parallel track. Phase 1 can start
against verified facts. ADR-0001 stays scoped to the web track.
