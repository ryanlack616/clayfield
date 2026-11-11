# Clayfield — Implementation Task List

Use this as the live execution checklist. Check an item only when its acceptance criteria are verified in the application or automated tests. Anchors are attached after the Phase 0 audit: each item names the file and line it changes, or names the file it creates. An item with no anchor is an item that will be built twice.

- Anchors verified against `src/` on 2026-11-11 (`361 passed, 7 skipped`, exit 0).
- Anchor format: `→ file:line` for an edit to existing code; `→ new: file` for a file that does not exist yet.
- The line numbers are the pre-build positions. Re-grep before editing; the tree moves.
- Phase numbers match the roadmap's 8-phase scheme. Gates live in the roadmap only; this list tracks the work and points at them.
- Metric definitions, mask semantics, and the calibrated fixture live in `docs-v3-build/MEASUREMENT_SPEC.md`; the metric tasks below implement that document.

## Shell decision — adapt, do not retrofit

The roadmap says "adapt" and the audit says "do not retrofit". They agree once the words are pinned down:

- **Retrofit** would mean re-skinning the current `QSplitter` and the 390 px overlay to look like the v3 mock. Rejected: float/tab/hide/persist are not expressible in a splitter, so the look would ship without the behaviour.
- **Adapt** means keeping the existing widget instances and changing only the container. `Viewport` (`src/clayfield/ui/viewport.py:63`), `ImagePanel` (`src/clayfield/ui/image_panel.py:86`), `TerrainPanel` (`src/clayfield/ui/terrain_panel.py:29`), `SculptPanel` (`src/clayfield/ui/sculpt_panel.py:35`), and `GpuImagePipeline` (`src/clayfield/ui/gpu_pipeline.py:28`) move into a `QDockWidget` shell. The geometry, terrain, sculpt and export code is not touched.

Concretely: `MainWindow` (`src/clayfield/ui/main_window.py:79`) is edited in place. The splitter at `src/clayfield/ui/main_window.py:150` and its `setCentralWidget` at `:169` are replaced; the panels are re-parented. Nothing is deleted until the new shell renders a relief through the same path (`_rebuild_heightfield`, `src/clayfield/ui/main_window.py:503`).

Roadmap authority: `docs-v3-build/IMPLEMENTATION_ROADMAP.md:67` ("Define main-window composition using the existing Qt patterns"), `:68` ("Implement or adapt dockable source and settings panels"), `:74` ("Preserve existing viewport interactions while integrating the new chrome"). Audit authority: `docs-v3-build/REPOSITORY_AUDIT.md:216` ("Do not attempt to retrofit the v3 layout onto the current splitter").

## Phase 0 — Repository audit and baseline

- [x] Record repository root, branch, working-tree status, and recent commit context.
- [x] Record Python version and dependency/install workflow.
- [x] Identify application entry point and launch command.
- [x] Identify main-window class and current widget hierarchy.
- [x] Identify existing dock/panel implementation and settings persistence.
- [x] Identify current viewport widget and rendering context.
- [x] Identify camera controls, lighting, materials, and overlays.
- [x] Identify source image loading and preprocessing code.
- [x] Identify image-to-heightfield conversion and pixel-to-mm mapping.
- [x] Identify mesh generation and current geometry ownership.
- [x] Identify Trimesh usage and any mesh repair/validation path.
- [x] Identify STL and 3MF export code.
- [x] Identify undo/redo, history, snapshots, and original-geometry retention.
- [x] Identify tests, fixtures, sample images, and test commands.
- [x] Run the current application and record baseline behavior.
- [x] Run existing tests and record baseline results.
- [x] Create `REPOSITORY_AUDIT.md` with exact paths, verified facts, gaps, and risks.

**Phase 0 gate:** owned by `docs-v3-build/IMPLEMENTATION_ROADMAP.md` § "Phase 0 — Repository audit and baseline" → Exit gate.

**Audit completed 2026-11-11** — report at `docs-v3-build/REPOSITORY_AUDIT.md`.
Baseline: 361 tests pass; window constructs and shows at 1309×820 with a valid
GL 4.6 context; `--gl-self-test` passes on `DISPLAY=:0` with
`XAUTHORITY=/run/user/1000/.mutter-Xwaylandauth.J78QY3`.

### Anchors established by the audit

| Fact | Anchor |
|---|---|
| Entry point | `main.py` → `clayfield.app.application:run` |
| Main window class | `src/clayfield/ui/main_window.py:79` |
| Default window size | `src/clayfield/ui/main_window.py:120` — `resize(1280, 820)` |
| Current layout | `src/clayfield/ui/main_window.py:150` — one `QSplitter` |
| Central widget | `src/clayfield/ui/main_window.py:169` |
| Bottom overlay width | `src/clayfield/ui/main_window.py:203` — `setFixedWidth(390)` |
| Settings store | `src/clayfield/ui/main_window.py:113` — `QSettings("ClayField", "ClayField")` |
| Dock widgets | none — `grep -rn QDockWidget src/` → 0 |
| Tab widgets | none — `grep -rn "QTabWidget\|addTab" src/` → 0 |
| Mask state | `src/clayfield/app/project_state.py:22,29,30,34` |
| Mask serialization | `src/clayfield/app/project_io.py:473,569` (16-bit PNG), `:573` (`mask_original.bin`) |
| Mask composition | `src/clayfield/field/composition.py:30,55-56` |
| Mask UI (radial only) | `src/clayfield/ui/image_panel.py:852-861`, import at `:1009` |
| Mask in viewport | none — `grep -ci mask ui/viewport.py ui/gpu_pipeline.py` → 0, 0 |
| Fabrication analysis | `src/clayfield/terrain/fabrication.py:71`, `:46` |
| Undo ledger | `src/clayfield/app/history.py:73` `EditLedger`, `:166` `ParameterHistory` |
| Export | `src/clayfield/export/stl.py:21`, `src/clayfield/export/three_mf.py:18`, `src/clayfield/export/verification.py:20,58` |

## Phase 1 — Architecture decisions and UI shell

- [ ] Create/adapt main window without replacing working processing/rendering components. → `src/clayfield/ui/main_window.py:79`; adapt in place per the shell decision above.
- [ ] Add compact geometric mark and CLAYFIELD wordmark. → `src/clayfield/ui/main_window.py:119` sets the title text; no icon asset exists (`QIcon` → 0 hits in `src/clayfield/ui/`); `src/clayfield/resources/` holds shaders only. New asset plus `setWindowIcon`.
- [ ] Add File / Edit / View / Tools / Help menus. → `src/clayfield/ui/main_window.py:296` `_build_menus`; current menus are File `:297`, Edit `:312`, View `:325`, Operations `:386`. Rename Operations → Tools, add Help.
- [ ] Implement source dock with left default placement. → content is `ImagePanel` (`src/clayfield/ui/image_panel.py:86`) wrapped in `image_scroll` (`src/clayfield/ui/main_window.py:151`). New `QDockWidget`.
- [ ] Implement settings dock with right default placement. → content is `TerrainPanel` (`src/clayfield/ui/terrain_panel.py:29`) wrapped in `terrain_scroll` (`src/clayfield/ui/main_window.py:154`); the 390 px `compose_overlay` (`:203`) currently carries the settings UI. New `QDockWidget`.
- [ ] Make docks resizable, movable, floatable, tabifiable, and hideable. → new: `QDockWidget.setFeatures`; no dock code exists today.
- [ ] Add Reset Layout command. → new action in `_build_menus` (`src/clayfield/ui/main_window.py:296`), default geometry held beside `QSettings` (`:113`).
- [ ] Persist dock arrangement and visibility between sessions. → `src/clayfield/ui/main_window.py:113` `QSettings("ClayField", "ClayField")` already exists; `saveState()`/`restoreState()` are new.
- [ ] Add horizontal workspace tabs: SOURCE / MODEL / SURFACE / CLEANUP / OUTPUT. → new `QTabWidget`; today the settings UI lives in the overlay assembled at `src/clayfield/ui/main_window.py:200-202`.
- [ ] Keep central 3D viewport persistent across tab changes. → `Viewport` (`src/clayfield/ui/viewport.py:63`) instantiated at `src/clayfield/ui/main_window.py:127`, added to the splitter at `:166`. Move it out of the splitter, keep the instance.
- [ ] Add status bar with truthful model and cursor information. → `src/clayfield/ui/main_window.py:126` `self.statusBar().addPermanentWidget(self.export_progress)`; `:172` `showMessage("Ready — ClayField")`.
- [ ] Apply shared visual tokens and common widget styling. → `src/clayfield/ui/theme.py:7` `apply_theme(dark)`; called at `src/clayfield/ui/main_window.py:114`. Tokens do not exist yet — `theme.py` has one function and no token constants.
- [ ] Add workspace-state preservation (scroll position, selections, values). → new; scroll areas are created inline at `src/clayfield/ui/main_window.py:151,154` and have no persistence.
- [ ] Add subtle tab transition without blocking interaction. → new.
- [ ] Verify default 1600 × 1000 logical-pixel layout. → `src/clayfield/ui/main_window.py:120` `resize(1280, 820)` must become 1600 × 1000; spec at `docs-v3-build/GUI_LAYOUT.md:30`. Measured floor is 1309 × 440, so 1600 × 1000 is reachable on this 3440 × 1440 display.
- [ ] Verify smaller-window behavior and high-DPI scaling. → `src/clayfield/ui/main_window.py:292` `resizeEvent`; overlay repositioning at `:275` `_position_canvas_overlays`.

**Phase 1 gate:** owned by `docs-v3-build/IMPLEMENTATION_ROADMAP.md` § "Phase 1 — Architecture decisions and UI shell" → Exit gate.

## Phase 2 — SOURCE and MODEL vertical slice

### SOURCE workspace

- [ ] Design no-image empty state with Open/Drop affordance. → `src/clayfield/ui/image_panel.py:86`; drop handling already exists at `src/clayfield/ui/main_window.py:390` `dragEnterEvent`, `:400` `dropEvent`.
- [ ] Implement one active source image at a time. → `src/clayfield/ui/image_panel.py:86` plus `src/clayfield/app/project_state.py`.
- [ ] Implement image preview with zoom, pan, Fit, and 1:1. → `image_panel.preview`, placed at `src/clayfield/ui/main_window.py:181`.
- [ ] Display filename and pixel dimensions. → `src/clayfield/ui/image_panel.py:332` `_update_provenance` (currently reports secondary/mask provenance only).
- [ ] Display transparency with subtle checkerboard background. → new drawing in `image_panel.preview`.
- [ ] Implement Replace Image behavior. → `src/clayfield/ui/image_panel.py:86`; loader at `src/clayfield/image/loader.py`.
- [ ] Bind brightness adjustment to actual processing path. → `src/clayfield/ui/gpu_pipeline.py:28` `GpuImagePipeline`; `src/clayfield/image/levels.py`.
- [ ] Bind contrast adjustment to actual processing path. → `src/clayfield/image/levels.py`, `src/clayfield/image/curves.py`.
- [ ] Bind gamma adjustment to actual processing path. → `src/clayfield/image/levels.py`, `src/clayfield/image/pipeline.py`.
- [ ] Bind invert toggle to actual processing path. → `src/clayfield/image/levels.py`.
- [ ] Implement rotate/flip only with clear reversible behavior. → `src/clayfield/image/geometry.py:52` `apply_image_geometry` (margins + resize; no rotate/flip yet).
- [ ] Decide crop support based on existing pipeline; do not expose a dead control. → **already implemented**: `src/clayfield/image/geometry.py:32` `crop_bounds`, `:52` `apply_image_geometry`. Expose it; the "decide" wording is stale.
- [ ] Mark relief stale when source changes. → `src/clayfield/ui/main_window.py:904` `_invalidate_heightfield`.


### MODEL workspace

- [ ] Add physical width numeric input with visible mm unit. → `src/clayfield/ui/terrain_panel.py:37` `self.width = self._dimension(100.0)`.
- [ ] Add physical height numeric input with visible mm unit. → `src/clayfield/ui/terrain_panel.py:39` `self.depth = self._dimension(100.0)`.
- [ ] Add aspect-ratio lock and verify source-ratio behavior. → `src/clayfield/ui/terrain_panel.py:436` `update_aspect_ratio`, wired at `src/clayfield/ui/main_window.py:133`.
- [ ] Add maximum relief depth input with visible mm unit. → `src/clayfield/ui/terrain_panel.py:44` `self.maximum = self._dimension(8.0)`.
- [ ] Add base thickness input with visible mm unit. → `src/clayfield/ui/terrain_panel.py:46` `self.base_thickness = self._dimension(5.0)`.
- [ ] Add resolution/mesh-density control based on actual pipeline capability. → `src/clayfield/ui/terrain_panel.py:117` `self.resolution` (32–2048), `:121` `self.export_resolution` (32–4096).
- [ ] Distinguish source pixels, heightfield samples, and output triangles. → `src/clayfield/geometry/estimates.py` for the triangle count; surface in the status bar (`src/clayfield/ui/main_window.py:126`).
- [ ] Add Generate/Update Relief action. → `src/clayfield/ui/main_window.py:503` `_rebuild_heightfield`, worker start at `:868` `_start_heightfield_worker`.
- [ ] Add processing progress and safe cancellation if supported. → `src/clayfield/ui/main_window.py:1120` `_export_progress` pattern; `src/clayfield/app/cancellation.py`, `src/clayfield/core/cancellation.py`.
- [ ] Frame model after successful generation. → `src/clayfield/ui/viewport.py:63`; camera at `src/clayfield/ui/camera.py:12` `OrbitCamera`.
- [ ] Mark geometry stale when generation parameters change. → `src/clayfield/ui/main_window.py:148` `parameters_changed.connect(self._rebuild_heightfield)`.

**Phase 2 gate:** owned by `docs-v3-build/IMPLEMENTATION_ROADMAP.md` § "Phase 2 — SOURCE and MODEL vertical slice" → Exit gate.

## Phase 3 — Geometry and mask contract

- [ ] Record the geometry representation per `MEASUREMENT_SPEC.md` §1. → `src/clayfield/geometry/mesh_generator.py` `generate_solid_mesh`; validated by `src/clayfield/geometry/validation.py`.
- [ ] Record the physical coordinate mapping per `MEASUREMENT_SPEC.md` §1.1. → `src/clayfield/terrain/mapping.py`.
- [ ] Record the mask sample domain and mapping per `MEASUREMENT_SPEC.md` §2.2. → `src/clayfield/app/project_state.py:29` `mask_field`; shape check at `src/clayfield/field/composition.py:30`.
- [ ] Implement mask validity, stale detection, and remap per `MEASUREMENT_SPEC.md` §2.2. → new; nothing in `src/` defines it.
- [ ] Implement weighted mask storage independent of geometry. → `src/clayfield/app/project_state.py:29`; serialized at `src/clayfield/app/project_io.py:473,569`. The storage exists; independence from geometry does not.
- [ ] Implement mask show/hide overlay. → new: `src/clayfield/ui/viewport.py:63` renders no mask (`grep -ci mask` → 0).
- [ ] Implement cyan eligible / dark-gray protected visualization. → new; no mask colour constants exist.
- [ ] Implement mask opacity control. → new.
- [ ] Implement Replace operation. → new mask op; `src/clayfield/ui/image_panel.py:852` radial mask only.
- [ ] Implement Add operation. → new mask op.
- [ ] Implement Subtract operation. → new mask op.
- [ ] Implement Invert operation. → new mask op; the existing `src/clayfield/ui/image_panel.py:861` "Invert mask" checkbox is radial-only.
- [ ] Implement Clear operation. → new mask op.
- [ ] Implement stale-mask detection. → new; needs a mapping-generation stamp beside `mask_source_descriptor` (`src/clayfield/app/project_state.py:22`).
- [ ] Add alignment tests for sample-to-geometry mapping. → new: `tests/`.
- [ ] Add tests that protected regions remain protected after mapping/resampling. → new: `tests/`.

**Phase 3 gate:** owned by `docs-v3-build/IMPLEMENTATION_ROADMAP.md` § "Phase 3 — Geometry and mask contract" → Exit gate.

## Phase 4 — First analysis and mask workflow (SURFACE workspace)

- [ ] Implement Detail Size per `MEASUREMENT_SPEC.md` §3.2. → new; only `analyze_heightfield` (`src/clayfield/terrain/fabrication.py:71`) exists and it measures fabrication limits.
- [ ] Implement Surface Roughness per `MEASUREMENT_SPEC.md` §3.3. → new.
- [ ] Implement Surface Irregularity per `MEASUREMENT_SPEC.md` §3.4. → new.
- [ ] Implement Isolated Peaks per `MEASUREMENT_SPEC.md` §3.6. → new.
- [ ] Implement Depressions per `MEASUREMENT_SPEC.md` §3.7. → new.
- [ ] Implement Edge Protection per `MEASUREMENT_SPEC.md` §3.8. → new.
- [ ] Verify physical scale limits against effective sampling resolution. → `src/clayfield/terrain/fabrication.py:46` `FabricationMetrics` already reports resolved feature width; extend rather than duplicate.
- [ ] Implement analysis preview without changing geometry or mask. → new module, e.g. `src/clayfield/terrain/surface_analysis.py`.
- [ ] Implement heatmap-replacement display mode. → new; `src/clayfield/ui/height_colors.py:110` `HeightColorDialog` is the existing colour path to copy.
- [ ] Implement translucent heatmap-over-clay display mode. → new shader pass in `src/clayfield/ui/gpu_pipeline.py:28`.
- [ ] Add legend, metric name, scale range, and units/convention. → new widget beside `src/clayfield/ui/histogram.py:11` `HistogramWidget`.
- [ ] Add detected-area summary only where meaningful. → new.
- [ ] Convert analysis output into weighted mask. → writes `state.mask_field` (`src/clayfield/app/project_state.py:29`).
- [ ] Add ANY/ALL combined detection after individual methods are validated. → new.
- [ ] Implement Curvature per `MEASUREMENT_SPEC.md` §3.5. → new.

**Phase 4 gate:** owned by `docs-v3-build/IMPLEMENTATION_ROADMAP.md` § "Phase 4 — First analysis and mask workflow" → Exit gate.

## Phase 5 — Mask editing and selective cleanup (CLEANUP workspace)

- [ ] Add cleanup tool selection. → `src/clayfield/ui/sculpt_panel.py:35` `SculptPanel`; brush settings at `src/clayfield/sculpt/brush.py:25` `BrushSettings`.
- [ ] Add brush radius in mm. → `src/clayfield/sculpt/brush.py:25`; cursor ring upload at `src/clayfield/ui/viewport.py:268`.
- [ ] Add brush strength control. → `src/clayfield/sculpt/brush.py:25`.
- [ ] Add brush falloff control. → `src/clayfield/sculpt/falloff.py`.
- [ ] Add brush flow control if required by stroke implementation. → `src/clayfield/sculpt/stroke.py`.
- [ ] Implement normal cursor with circle and falloff visualization. → partially present: ring cursor at `src/clayfield/ui/viewport.py:87,269,382`. Falloff band is new.
- [ ] Implement advanced cursor with center and strength information. → new; extends `src/clayfield/ui/viewport.py:268`.
- [ ] Implement contextual floating palette. → new; nearest existing pattern is `compose_overlay` at `src/clayfield/ui/main_window.py:203`.
- [ ] Support moving and pinning the floating palette. → new.
- [ ] Keep full controls in CLEANUP panel. → `src/clayfield/ui/sculpt_panel.py:35`, shown/hidden at `src/clayfield/ui/main_window.py:241` `_set_sculpt_panel_visible`.
- [ ] Implement manual mask paint. → new; no mask editor class exists in `src/`.
- [ ] Implement manual mask erase. → new.
- [ ] Implement mask expand. → new morphology op.
- [ ] Implement mask contract. → new morphology op.
- [ ] Implement mask feather. → new; `src/clayfield/ui/image_panel.py:858` `mask_feather` is a radial-composition parameter, not a mask op.
- [ ] Implement mask threshold. → new.
- [ ] Implement mask-aware smoothing. → new; `src/clayfield/sculpt/smooth_bilateral.py`, `smooth_laplacian.py`, `smooth_taubin.py` are unmasked today.
- [ ] Validate Bilateral filter behavior if heightfield representation supports it. → `src/clayfield/sculpt/smooth_bilateral.py`.
- [ ] Implement median/spike cleanup if supported. → new.
- [ ] Implement noise removal if supported. → new.
- [ ] Add Preview / Apply / Cancel lifecycle. → new; no preview lifecycle exists for mask ops.
- [ ] Ensure Cancel restores pre-preview state. → `src/clayfield/sculpt/session.py:22` `SculptSession`, `src/clayfield/sculpt/history.py:80` `SculptHistory`.
- [ ] Ensure protected regions are unchanged within defined tolerance. → new; depends on Phase 3's mask mapping.
- [ ] Add explicit temporary mask-bypass control. → new.
- [ ] Add before/after toggle. → new.
- [ ] Add operation history with meaningful names. → `src/clayfield/app/history.py:73` `EditLedger.record(kind)`.
- [ ] Integrate geometry and mask changes into undo/redo. → `src/clayfield/app/history.py:73`; mask edits need a new ledger kind per `docs-v3-build/REPOSITORY_AUDIT.md:208-209`.
- [ ] Define and test Restore Original Surface behavior before exposing the brush. → `src/clayfield/app/project_state.py:34` `mask_original_bytes` and `src/clayfield/app/project_io.py:573` are the retained-original path; geometry original retention is new.

**Phase 5 gate:** owned by `docs-v3-build/IMPLEMENTATION_ROADMAP.md` § "Phase 5 — Mask editing and selective cleanup" → Exit gate.

## Phase 6 — OUTPUT and fabrication validation

- [ ] Add STL export option. → `src/clayfield/export/stl.py:21` `export_stl`; UI at `src/clayfield/ui/main_window.py:966` `_export_stl`.
- [ ] Add 3MF export option. → `src/clayfield/export/three_mf.py:18` `export_3mf`; UI at `src/clayfield/ui/main_window.py:969` `_export_3mf`.
- [ ] Add filename and destination controls. → `src/clayfield/ui/main_window.py:972` `_start_mesh_export`.
- [ ] Keep basic export path simple. → `src/clayfield/ui/main_window.py:972`.
- [ ] Add expandable advanced settings. → `src/clayfield/ui/export_preview.py:23` `ExportPreviewDialog`.
- [ ] Display physical dimensions. → `src/clayfield/geometry/estimates.py`; `src/clayfield/ui/main_window.py:688` `_final_export_analysis`.
- [ ] Display total thickness. → `src/clayfield/terrain/fabrication.py:46` `base thickness`.
- [ ] Display triangle count. → `src/clayfield/geometry/estimates.py`.
- [ ] Validate watertightness where supported. → `src/clayfield/export/verification.py:20` `verify_stl_export`, `:58` `verify_3mf_export`.
- [ ] Validate non-manifold edges where supported. → `src/clayfield/geometry/validation.py`.
- [ ] Validate isolated/disconnected components where supported. → `src/clayfield/geometry/validation.py`.
- [ ] Distinguish pass, fail, not run, and unsupported validation states. → new tri-state reporting; `src/clayfield/export/verification.py:20,58` raise today.
- [ ] Ensure export does not mutate working geometry. → `src/clayfield/export/tasks.py` worker wrappers; verify against `geometry/container.py`.
- [ ] Re-import representative exports and verify bounds/topology. → new: `tests/` using `src/clayfield/export/verification.py:20,58`.

**Phase 6 gate:** owned by `docs-v3-build/IMPLEMENTATION_ROADMAP.md` § "Phase 6 — OUTPUT and fabrication validation" → Exit gate.

## Phase 7 — Polish, performance, and release hardening

- [ ] Verify all controls have consistent hover, focus, active, disabled, and error states. → `src/clayfield/ui/theme.py:7` `apply_theme`; token set is new.
- [ ] Verify units are visible and values are directly editable. → `src/clayfield/ui/terrain_panel.py:37-46`; `_dimension` helper already appends the unit.
- [ ] Verify icon-only controls have tooltips/accessibility names. → `src/clayfield/ui/sculpt_panel.py:35`, `src/clayfield/ui/export_preview.py:23`.
- [ ] Verify keyboard shortcuts do not conflict with text editing. → `src/clayfield/ui/main_window.py:296` `_build_menus`.
- [ ] Verify empty, loading, stale, failed, completed, and cancelled states. → `src/clayfield/ui/main_window.py:960` `_heightfield_failed`, `:1124` `_export_finished`, `:904` `_invalidate_heightfield`.
- [ ] Verify status bar never displays stale or fabricated values. → `src/clayfield/ui/main_window.py:126,172`.
- [ ] Profile large image processing. → `src/clayfield/image/pipeline.py`, `field/pipeline.py`.
- [ ] Profile dense mesh viewport performance. → `src/clayfield/ui/viewport.py:182` `paintGL`; `src/clayfield/ui/gpu_pipeline.py:28`.
- [ ] Profile undo/history memory use. → `src/clayfield/app/history.py:166` `ParameterHistory` (`limit=100`).
- [ ] Verify long operations do not freeze the Qt event loop. → `src/clayfield/app/worker.py`.
- [ ] Verify high-DPI scaling. → `src/clayfield/ui/main_window.py:292` `resizeEvent`.
- [ ] Verify dock persistence after restart. → `src/clayfield/ui/main_window.py:113` `QSettings`.
- [ ] Verify Reset Layout restores the default arrangement. → new command added in Phase 1.
- [ ] Verify clean-environment installation and launch. → `pyproject.toml`, `uv.lock`, `.venv`; `python -m clayfield --self-test`.
- [ ] Update user-facing documentation and shortcuts reference. → `docs-v3-build/` plus the root `README.md`.

**Phase 7 gate:** owned by `docs-v3-build/IMPLEMENTATION_ROADMAP.md` § "Phase 7 — Polish, performance, and release hardening" → Exit gate.

---

## First implementation sprint — bounded scope

Do not start by implementing all analysis methods. The first sprint should focus on the shell and integration seam:

- [x] Complete repository audit. → `docs-v3-build/REPOSITORY_AUDIT.md`.
- [x] Record current main-window and viewport architecture. → audit §"Main window" (`:98-109`) and §"Baseline launch behavior" (`:74-96`).
- [ ] Build dockable shell and five tabs around the existing viewport. → `src/clayfield/ui/main_window.py:79`; replace splitter `:150` and central widget `:169`; keep `Viewport` (`src/clayfield/ui/viewport.py:63`) instance from `:127`.
- [ ] Add theme tokens and shared control styling. → `src/clayfield/ui/theme.py:7`.
- [ ] Preserve viewport rendering and navigation. → `src/clayfield/ui/viewport.py:182` `paintGL`; `src/clayfield/ui/camera.py:12` `OrbitCamera` — no edits expected.
- [ ] Add layout persistence and Reset Layout. → `src/clayfield/ui/main_window.py:113` `QSettings`.
- [ ] Verify the application still generates and displays a relief through the existing path. → `src/clayfield/ui/main_window.py:503` `_rebuild_heightfield`, `:868` `_start_heightfield_worker`, `:913` `_heightfield_finished`.

**Sprint exit:** The redesigned shell runs with the existing working relief workflow. No geometry/analysis rewrite has been introduced.

## Change-control rules

- Do not check off a task because code was written; check it after behavior is tested.
- Anchors are attached; re-grep the line before editing. A moved line is a stale anchor, not a moved intent.
- If a task is blocked by missing capability, record the blocker and a smallest-scope alternative.
- If a task requires a new dependency, justify it against the existing stack before adding it.
- Keep the first end-to-end slice small and measurable.
