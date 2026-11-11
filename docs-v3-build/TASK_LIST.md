# Clayfield — Implementation Task List

Use this as the live execution checklist. Check an item only when its acceptance criteria are verified in the application or automated tests. Add repository-specific file paths after the audit; do not guess paths in advance.

## Phase 0 — Repository audit

- [ ] Record repository root, branch, working-tree status, and recent commit context.
- [ ] Record Python version and dependency/install workflow.
- [ ] Identify application entry point and launch command.
- [ ] Identify main-window class and current widget hierarchy.
- [ ] Identify existing dock/panel implementation and settings persistence.
- [ ] Identify current viewport widget and rendering context.
- [ ] Identify camera controls, lighting, materials, and overlays.
- [ ] Identify source image loading and preprocessing code.
- [ ] Identify image-to-heightfield conversion and pixel-to-mm mapping.
- [ ] Identify mesh generation and current geometry ownership.
- [ ] Identify Trimesh usage and any mesh repair/validation path.
- [ ] Identify STL and 3MF export code.
- [ ] Identify undo/redo, history, snapshots, and original-geometry retention.
- [ ] Identify tests, fixtures, sample images, and test commands.
- [ ] Run the current application and record baseline behavior.
- [ ] Run existing tests and record baseline results.
- [ ] Create `REPOSITORY_AUDIT.md` with exact paths, verified facts, gaps, and risks.

**Phase 0 acceptance:** Audit report is complete; current launch/test state is known; no source code has been changed merely to begin the audit.

## Phase 1 — Application shell

- [ ] Create/adapt main window without replacing working processing/rendering components.
- [ ] Add compact geometric mark and CLAYFIELD wordmark.
- [ ] Add File / Edit / View / Tools / Help menus.
- [ ] Implement source dock with left default placement.
- [ ] Implement settings dock with right default placement.
- [ ] Make docks resizable, movable, floatable, tabifiable, and hideable.
- [ ] Add Reset Layout command.
- [ ] Persist dock arrangement and visibility between sessions.
- [ ] Add horizontal workspace tabs: SOURCE / MODEL / SURFACE / CLEANUP / OUTPUT.
- [ ] Keep central 3D viewport persistent across tab changes.
- [ ] Add status bar with truthful model and cursor information.
- [ ] Apply shared visual tokens and common widget styling.
- [ ] Add workspace-state preservation (scroll position, selections, values).
- [ ] Add subtle tab transition without blocking interaction.
- [ ] Verify default 1600 × 1000 logical-pixel layout.
- [ ] Verify smaller-window behavior and high-DPI scaling.

**Phase 1 acceptance:** Docking, tabs, persistent viewport, styling, and state persistence work without breaking the existing viewport or geometry pipeline.

## Phase 2 — SOURCE workspace

- [ ] Design no-image empty state with Open/Drop affordance.
- [ ] Implement one active source image at a time.
- [ ] Implement image preview with zoom, pan, Fit, and 1:1.
- [ ] Display filename and pixel dimensions.
- [ ] Display transparency with subtle checkerboard background.
- [ ] Implement Replace Image behavior.
- [ ] Bind brightness adjustment to actual processing path.
- [ ] Bind contrast adjustment to actual processing path.
- [ ] Bind gamma adjustment to actual processing path.
- [ ] Bind invert toggle to actual processing path.
- [ ] Implement rotate/flip only with clear reversible behavior.
- [ ] Decide crop support based on existing pipeline; do not expose a dead control.
- [ ] Mark relief stale when source changes.

**Phase 2 acceptance:** One image can be loaded, inspected, adjusted, and replaced; source state and relief-stale state are clear.

## Phase 3 — MODEL workspace

- [ ] Add physical width numeric input with visible mm unit.
- [ ] Add physical height numeric input with visible mm unit.
- [ ] Add aspect-ratio lock and verify source-ratio behavior.
- [ ] Add maximum relief depth input with visible mm unit.
- [ ] Add base thickness input with visible mm unit.
- [ ] Add resolution/mesh-density control based on actual pipeline capability.
- [ ] Distinguish source pixels, heightfield samples, and output triangles.
- [ ] Add Generate/Update Relief action.
- [ ] Add processing progress and safe cancellation if supported.
- [ ] Frame model after successful generation.
- [ ] Mark geometry stale when generation parameters change.

**Phase 3 acceptance:** Image-to-relief workflow produces correct physical bounds and the UI reports truthful dimensions and mesh statistics.

## Phase 4 — Geometry and mask contract

- [ ] Document authoritative editable geometry representation.
- [ ] Document physical coordinate mapping.
- [ ] Document mask sample domain and mapping to geometry.
- [ ] Define mask behavior on geometry regeneration/resampling.
- [ ] Implement weighted mask storage independent of geometry.
- [ ] Implement mask show/hide overlay.
- [ ] Implement cyan eligible / dark-gray protected visualization.
- [ ] Implement mask opacity control.
- [ ] Implement Replace operation.
- [ ] Implement Add operation.
- [ ] Implement Subtract operation.
- [ ] Implement Invert operation.
- [ ] Implement Clear operation.
- [ ] Implement stale-mask detection.
- [ ] Add alignment tests for sample-to-geometry mapping.
- [ ] Add tests that protected regions remain protected after mapping/resampling.

**Phase 4 acceptance:** Mask remains spatially aligned, independent from geometry, and cannot silently apply after its mapping becomes invalid.

## Phase 5 — SURFACE analysis

- [ ] Define and document Detail Size metric.
- [ ] Define and document Surface Roughness metric.
- [ ] Define and document Surface Irregularity metric.
- [ ] Define and document Isolated Peaks metric.
- [ ] Define and document Depressions metric.
- [ ] Define and document Edge Protection metric.
- [ ] Verify physical scale limits against effective sampling resolution.
- [ ] Implement analysis preview without changing geometry or mask.
- [ ] Implement heatmap-replacement display mode.
- [ ] Implement translucent heatmap-over-clay display mode.
- [ ] Add legend, metric name, scale range, and units/convention.
- [ ] Add detected-area summary only where meaningful.
- [ ] Convert analysis output into weighted mask.
- [ ] Add ANY/ALL combined detection after individual methods are validated.
- [ ] Add Curvature only after its metric and interpretation are documented.

**Phase 5 acceptance:** At least one method detects a known physical test feature, produces a readable preview, and generates a correctly aligned weighted mask.

## Phase 6 — CLEANUP and brush workflow

- [ ] Add cleanup tool selection.
- [ ] Add brush radius in mm.
- [ ] Add brush strength control.
- [ ] Add brush falloff control.
- [ ] Add brush flow control if required by stroke implementation.
- [ ] Implement normal cursor with circle and falloff visualization.
- [ ] Implement advanced cursor with center and strength information.
- [ ] Implement contextual floating palette.
- [ ] Support moving and pinning the floating palette.
- [ ] Keep full controls in CLEANUP panel.
- [ ] Implement manual mask paint.
- [ ] Implement manual mask erase.
- [ ] Implement mask expand.
- [ ] Implement mask contract.
- [ ] Implement mask feather.
- [ ] Implement mask threshold.
- [ ] Implement mask-aware smoothing.
- [ ] Validate Bilateral filter behavior if heightfield representation supports it.
- [ ] Implement median/spike cleanup if supported.
- [ ] Implement noise removal if supported.
- [ ] Add Preview / Apply / Cancel lifecycle.
- [ ] Ensure Cancel restores pre-preview state.
- [ ] Ensure protected regions are unchanged within defined tolerance.
- [ ] Add explicit temporary mask-bypass control.
- [ ] Add before/after toggle.
- [ ] Add operation history with meaningful names.
- [ ] Integrate geometry and mask changes into undo/redo.
- [ ] Define and test Restore Original Surface behavior before exposing the brush.

**Phase 6 acceptance:** A known local defect can be detected, masked, refined, compared, and undone without altering protected regions beyond a documented tolerance.

## Phase 7 — OUTPUT and validation

- [ ] Add STL export option.
- [ ] Add 3MF export option.
- [ ] Add filename and destination controls.
- [ ] Keep basic export path simple.
- [ ] Add expandable advanced settings.
- [ ] Display physical dimensions.
- [ ] Display total thickness.
- [ ] Display triangle count.
- [ ] Validate watertightness where supported.
- [ ] Validate non-manifold edges where supported.
- [ ] Validate isolated/disconnected components where supported.
- [ ] Distinguish pass, fail, not run, and unsupported validation states.
- [ ] Ensure export does not mutate working geometry.
- [ ] Re-import representative exports and verify bounds/topology.

**Phase 7 acceptance:** STL and 3MF export correctly; displayed validation state is truthful; exported dimensions match the model.

## Phase 8 — Polish and release hardening

- [ ] Verify all controls have consistent hover, focus, active, disabled, and error states.
- [ ] Verify units are visible and values are directly editable.
- [ ] Verify icon-only controls have tooltips/accessibility names.
- [ ] Verify keyboard shortcuts do not conflict with text editing.
- [ ] Verify empty, loading, stale, failed, completed, and cancelled states.
- [ ] Verify status bar never displays stale or fabricated values.
- [ ] Profile large image processing.
- [ ] Profile dense mesh viewport performance.
- [ ] Profile undo/history memory use.
- [ ] Verify long operations do not freeze the Qt event loop.
- [ ] Verify high-DPI scaling.
- [ ] Verify dock persistence after restart.
- [ ] Verify Reset Layout restores the default arrangement.
- [ ] Verify clean-environment installation and launch.
- [ ] Update user-facing documentation and shortcuts reference.

**Phase 8 acceptance:** Core workflow is stable, responsive, visually consistent, and reproducible from a clean install.

---

## First implementation sprint — bounded scope

Do not start by implementing all analysis methods. The first sprint should focus on the shell and integration seam:

- [ ] Complete repository audit.
- [ ] Record current main-window and viewport architecture.
- [ ] Build dockable shell and five tabs around the existing viewport.
- [ ] Add theme tokens and shared control styling.
- [ ] Preserve viewport rendering and navigation.
- [ ] Add layout persistence and Reset Layout.
- [ ] Verify the application still generates and displays a relief through the existing path.

**Sprint exit:** The redesigned shell runs with the existing working relief workflow. No geometry/analysis rewrite has been introduced.

## Change-control rules

- Do not check off a task because code was written; check it after behavior is tested.
- Add exact repository paths and relevant class/function names after the audit.
- If a task is blocked by missing capability, record the blocker and a smallest-scope alternative.
- If a task requires a new dependency, justify it against the existing stack before adding it.
- Keep the first end-to-end slice small and measurable.
