# ClayField Roadmap — Archived Batch Checklist

This document preserves the historical batch plan. Its individual checkboxes
and status notes are outdated; do not use them to assess the current build.
See [roadmap.md](roadmap.md) for the current task plan.

The archive describes the 0.2.0 state and intentionally does not track later
0.3.0 work such as GPU spatial filters, crop/resize, presets, cross-sections,
export preview, and local print-QA artifacts.

## Current status — 0.2.0

- Image loading, adjustment processing, heightfields, autosave and exports run
  on background workers, with stale-result protection.
- Undo/redo, recent projects, recovery, camera fitting, lighting, progress, and
  8/16-bit PNG/TIFF heightmap output are available.
- At the time of this archived 0.2.0 snapshot, OpenGL tonal previews and CPU
  agreement tests were implemented; CPU heightfields remained authoritative for
  export. The current 0.3.0 build also supports GPU blur and sharpen previews.
- STL and 3MF exports are placed flat on a Z-up build plate. Both have been
  opened and sliced in PrusaSlicer; lib3mf independently verifies 3MF meshes.
- A Linux PyInstaller bundle, clean-install checks, real-context GPU tests,
  optional slicer tests, and large-array stress tests are available.

Further refinement includes GPU spatial filters, broader hardware/distribution
testing, more granular cancellation during STL validation, and publishing a
tagged release. Advanced tools remain future work.

The batch checklist below records the historical development plan. Some of its
individual checkbox annotations predate the status above.

## Status legend

- `[x]` Complete and verified.
- `[~]` Partially implemented or needs refinement.
- `[ ]` Planned.

---

## Completed foundation batches

### Batch 1 — Application foundation `[x]`

- PySide6 desktop application shell.
- Three-panel layout.
- OpenGL 3.3 Core viewport.
- Orbit camera, zoom, and camera presets.
- Reference grid.
- Packaged GLSL resources.
- GPU resource cleanup.
- Installable `clayfield` console entry point.

**Verification:** GUI startup smoke test and packaged launcher test pass.

### Batch 2 — Image import and grayscale `[x]`

- PNG, JPEG, TIFF, and BMP loading.
- 8-bit and 16-bit source preservation.
- Grayscale conversion.
- Non-destructive inversion.
- Image preview and metadata display.
- Invalid image error handling.

**Verification:** image loader and grayscale tests pass.

### Batch 3 — Image adjustments `[x]`

- Levels.
- Gamma.
- Brightness and contrast.
- Blur.
- Sharpen.
- Threshold enable/disable.
- Histogram.
- Interactive curve editor.
- Adjustment reset.
- Central adjusted-image state.

**Verification:** adjustment tests and GUI smoke test pass.

### Batch 4 — Heightfield and terrain preview `[x]`

- Physical dimensions in millimeters.
- Minimum and maximum height.
- Positive and negative relief modes.
- Preview resolution.
- CPU-authoritative physical heightfield.
- GPU floating-point height texture.
- GPU vertex displacement.
- Lit terrain surface.
- Camera fit and view presets.

**Verification:** heightfield tests, OpenGL shader startup, and GUI smoke test pass.

### Batch 5 — Solid mesh generation `[x]`

- Closed positive relief solids.
- Closed negative relief solids.
- Configurable base thickness.
- Watertightness validation.
- Positive-volume validation.
- Finite-coordinate validation.
- Degenerate-face validation.

**Verification:** mesh generation and validation tests pass.

### Batch 6 — Export and projects `[x]`

- STL export.
- 3MF export.
- 16-bit PNG heightmap export.
- Native `.clayfield` project format.
- Embedded source image.
- Terrain and adjustment persistence.
- Curve-point persistence.
- Project version validation.
- Dirty-state tracking.
- Unsaved-close protection.
- Independent preview/export resolution.

**Verification:** export, project round-trip, malformed-project, wheel-build, and GUI tests pass.

### Batch 7 — Packaging and CI `[x]`

- Editable installation.
- `clayfield` launcher.
- Packaged shader resources.
- Wheel build verification.
- GitHub Actions compilation check.
- GitHub Actions pytest check.
- GitHub Actions wheel build.
- README documentation.

**Verification:** wheel contains shader resources and local test suite passes.

---

## Next implementation batches

### Batch 8 — Background processing `[~]` — highest priority

Move expensive work off the Qt UI thread.

- Worker abstraction using `QThreadPool`/`QRunnable`. `[x]`
- Background heightfield generation. `[x]`
- Generation-token stale-result protection. `[x]`
- Background image adjustment processing. `[x]`
- Background mesh generation. `[x]` for STL/3MF export tasks.
- Background STL/3MF export. `[x]`
- Background heightmap export. `[x]`
- Progress reporting. `[x]` for STL, 3MF, and heightmap export.
- Cancellation support. `[x]` for STL, 3MF, and heightmap export.
- Busy-state UI controls. `[x]` via active-export guard and status messages.
- Worker error propagation. `[x]` for heightfield, adjustment, and mesh export paths.
- Stale-result protection when parameters change rapidly. `[x]` for heightfield and adjustment paths.

**Exit criteria:** large-image operations keep the UI responsive and cancellation is reliable. Heightfield, image-adjustment, STL/3MF mesh export, and heightmap export operations are asynchronous. Cooperative export cancellation and staged percentage progress are implemented.

### Batch 9 — Project fidelity and recovery `[~]`

- Persist invert state explicitly. `[x]`
- Persist complete adjustment ordering.
- Restore exact adjusted-image state. `[~]` — image parameters, inversion, curves, smoothing, and edge falloff restore; broader pipeline verification remains. `[~]` — inversion and adjustment values restore; full pipeline-state verification remains.
- Atomic project saves. `[x]`
- Autosave/recovery snapshots.
- Recent-project list.
- Open/New Project unsaved-change prompt. `[x]`
- Visible dirty-state title marker. `[x]`
- Project migration framework.

**Dependency:** Batch 8 is not required, but persistence should be stable before adding recovery.

### Batch 10 — Terrain controls `[ ]`

- Aspect-ratio-preserving width/depth behavior.
- Width/depth lock toggle.
- Edge falloff.
- Smoothing.
- Noise.
- Height mapping curve separate from image curve.
- Physical minimum-wall-thickness checks.
- Terrain parameter presets.
- Preview/export resolution labels and estimates. `[~]` — separate controls and aspect-ratio-derived heights are implemented.

**Exit criteria:** terrain settings visibly and predictably control physical output.

### Batch 11 — Mesh performance and quality `[ ]`

- Adaptive mesh resolution.
- Mesh simplification/decimation.
- Triangle-count estimate.
- Memory estimate.
- Large-mesh safeguards.
- Better side-wall handling for extreme relief.
- Mesh winding/orientation diagnostics.
- Export-ready normals.

**Dependency:** Batch 10 should stabilize terrain semantics first.

### Batch 12 — Export validation `[ ]`

- Reopen exported STL with Trimesh.
- Validate 3MF with an external-compatible reader.
- Binary/text STL options.
- TIFF heightmap export.
- PNG/TIFF bit-depth selection.
- Export preview.
- Export warnings for large files.
- Output metadata and units verification.

**Exit criteria:** exported files are independently reopenable and validated.

### Batch 13 — Image workflow refinement `[ ]`

- Drag-and-drop image loading.
- Drag-and-drop project loading.
- EXIF orientation handling.
- Alpha-channel policy.
- Linear-light/color-managed processing.
- Interactive histogram controls.
- Curve-point deletion.
- Curve presets.
- Smooth curve interpolation.
- Levels output black/white controls.
- Better error dialogs.

### Batch 14 — Viewport refinement `[~]`

- Pan interaction.
- Clipping-plane controls.
- Solid/wireframe toggle.
- Height-based coloring.
- Material controls.
- Better edge normals.
- Improved fit behavior for extreme aspect ratios.
- Persistent GPU buffer updates.
- Viewport performance benchmarks.

### Batch 15 — Testing and release automation `[~]`

- Qt widget tests.
- Camera interaction tests.
- Project UI tests.
- GPU texture upload tests where context is available.
- Large-image benchmarks.
- Mesh stress tests.
- CI artifact publishing.
- Clean-environment wheel installation test.
- Changelog and release notes.
- Versioned release process.

---

## Recommended execution order

1. Batch 8 — Background processing.
2. Batch 9 — Project fidelity and recovery.
3. Batch 10 — Terrain controls.
4. Batch 11 — Mesh performance and quality.
5. Batch 12 — Export validation.
6. Batch 13 — Image workflow refinement.
7. Batch 14 — Viewport refinement.
8. Batch 15 — Testing and release automation.

## Current project health

- CPU tests: passing.
- GUI startup: passing.
- OpenGL shader startup: passing.
- Packaged wheel: verified.
- Installed launcher: verified.
- Native project round-trip: passing.
- STL export: passing.
- 3MF package generation: passing basic package checks.
- Heightmap export: passing.
- Large exports remain bounded by a conservative memory estimate; very large
  meshes and additional GPU/desktop configurations need further field testing.
