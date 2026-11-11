# ClayField Task Plan

The detailed V2 product roadmap is maintained in
[V2-MASTER-PLAN.md](V2-MASTER-PLAN.md). This file tracks the current 2.0.0
baseline and short-term release work; the master plan governs the procedural
height-field, fabrication-analysis, and external heightmap/mask interchange.

The executable V2 checklist is maintained in
[V2-BUILD-TASK-LIST.md](V2-BUILD-TASK-LIST.md). Build batches must be completed
in order and closed through their gates before moving to release hardening.

The current local acceptance state is summarized in
[docs/V2-ACCEPTANCE-REPORT.md](../docs/V2-ACCEPTANCE-REPORT.md).

The clean canonical master list is
[V2-MASTER-TASK-LIST.md](V2-MASTER-TASK-LIST.md). Use it for day-to-day status
updates; the older build board remains as the detailed historical checklist.

The single canonical completion roadmap is
[V2-CANONICAL-ROADMAP.md](V2-CANONICAL-ROADMAP.md). Use that file when choosing
the next batch or closing a release gate.

Post-V2 generator expansion is tracked in
[V2-PATTERN-SOURCES-PLAN.md](V2-PATTERN-SOURCES-PLAN.md).

The planned client-side web rewrite is split into two builds:
[mesh-forge/README.md](../mesh-forge/README.md) (reusable core; see its
[roadmap](../mesh-forge/ROADMAP.md) and [task list](../mesh-forge/TASK-LIST.md)) and
[clayfield-web/README.md](../clayfield-web/README.md) (the app on that core; see its
[roadmap](../clayfield-web/ROADMAP.md) and [task list](../clayfield-web/TASK-LIST.md)).
All docs: [docs/README.md](../docs/README.md).

V2 is organized into six manageable build batches: baseline/contracts, field
engine, pipeline/fabrication, persistence/workers, product UI/external imports,
and production hardening/release.

Status: `[x]` complete, `[~]` partially complete, `[ ]` remaining.

## Completed — 0.2.0 and 0.3.0

- [x] Desktop application, image adjustments, terrain controls, and 3D preview.
- [x] Repair OpenGL context handling; verify terrain rendering on the development GPU.
- [x] Export watertight STL and 3MF solids, oriented flat on the build plate.
- [x] Open and slice both mesh formats in PrusaSlicer; check 3MF with lib3mf.
- [x] Add undo/redo, project persistence, autosave/recovery, and recent projects.
- [x] Run image loading, adjustments, heightfields, autosave, and exports in workers.
- [x] Improve mesh construction, memory estimates, camera fitting, lighting, and export progress.
- [x] Add 8/16-bit PNG and TIFF heightmap exports.
- [x] Add GPU tonal previews and CPU/GPU agreement tests, with CPU-authoritative export.
- [x] Build a Linux bundle and wheel; verify clean installation and packaged OpenGL startup.
- [x] Add GUI, GPU, slicer, and stress tests, documentation, and CI artifact configuration.
- [x] Debounce edits, cache image-processing stages, and improve cancellation and project migration.
- [x] Add GPU blur/sharpen and direct GPU-to-viewport previews without preview readback.
- [x] Add crop/resize, independent height mapping, modifier strengths, fractal noise, and presets.
- [x] Add image/heightmap comparison, height range, and minimum-wall feedback.
- [x] Add orthographic projection, grid visibility, dark theme, sliders, reset controls, and export preview.
- [x] Add cross-section inspection with physical distance and height range readouts.

The latest full local run passed **118 tests**, including OpenGL, stress, and
PrusaSlicer checks. NVIDIA and Mesa software OpenGL checks passed; the 2.0.0
wheel and Linux bundle passed clean-install and graphics self-tests. The bundle
archive is `dist/clayfield-2.0.0-linux-x86_64.tar.gz`; the executable is
`dist/2.0.0/clayfield/clayfield`. The desktop 2.0.0 release is intentionally
local-only; remote CI, online publishing, and GitHub integration are not part
of that release process. The planned web builds (`mesh-forge/`,
`clayfield-web/`) do add CI gates.

Digital print QA artifacts are in `dist/print-qa/`: STL and 3MF are 60 × 40 ×
8 mm, manifold, and both produced G-code through PrusaSlicer. Physical print
inspection remains unavailable without a printer.

## Next actions — recommended order

1. Test the wheel and bundle on additional Ubuntu versions and GPU drivers when available.
2. Produce and inspect physical prints for dimensions, orientation, and detail when available.
3. Investigate finer-grained cancellation for long validation operations.

Online CI, remote publishing, and GitHub integration are intentionally deferred.
Additional Ubuntu installations and a physical 3D printer are not available in
the development environment.

## Progress by requested area

### 1. Release and field validation

- [ ] Run CI on the repository and address any platform-specific failures.
- [ ] Test the wheel and bundle on additional supported Ubuntu versions and GPU drivers.
- [ ] Validate real prints and check relief orientation, dimensions, and surface detail.
- [ ] Publish a tagged release and its verified artifacts.

Local validation includes NVIDIA and Mesa 26.0.8 software rendering on Ubuntu
26.04, plus STL and 3MF slicing in PrusaSlicer.

### 2. Responsiveness and reliability

- [x] Add cancellation checkpoints for chunked mesh generation and STL writing.
- [~] Add validation-stage cancellation checkpoints; individual Trimesh/OpenCV calls remain indivisible.
- [x] Debounce rapid edits and cache unaffected image-processing stages.
- [x] Benchmark large images and meshes and retain conservative export safeguards.
- [x] Migrate version 1/2/3 projects to version 4 and add recovery/compatibility tests.

### 3. GPU processing

- [x] Extend GPU processing to blur and sharpen, with CPU/GPU agreement tests.
- [x] Support bounded previews up to 4,194,304 pixels directly from GPU textures; exports remain CPU-authoritative.
- [~] Test CPU/GPU agreement on additional graphics drivers (Mesa software and NVIDIA verified; more hardware remains).

GPU previews also use a workload limit and fall back to the CPU for terrain
modifiers or unsupported settings.

### 4. Image and terrain workflow

- [x] Add non-destructive crop and image resize controls.
- [x] Add separate height inversion, offset, scale, normalize, and clamp controls.
- [x] Add smoothing strength, edge-falloff strength, and fractal-noise controls.
- [x] Add terrain/adjustment presets and minimum-wall-thickness feedback.
- [x] Add original/adjusted/final-heightmap comparison and height-range display.

### 5. Interface and export refinement

- [x] Add orthographic projection and grid visibility controls.
- [x] Add an export preview and dimensions/validation summary.
- [x] Add a dark theme, sliders, tooltips, and section-level reset controls.
- [x] Expand GUI interaction, project round-trip, and export regression coverage.

## Future extensions

- [x] Cross-section preview.
- [ ] Circular bases and beveled borders.
- [ ] Tile repetition and ceramic shrinkage/mold-release tools.
- [ ] Procedural generators, local displacement, masks, and sculpting tools.

V2 replaces the broad procedural-generator item above with the staged plan in
the master document: first-class deterministic sources, field composition,
fixed-range physical mapping, fabrication warnings, procedural project
persistence, external heightmap/mask interchange, and production hardening.

See [development.md](../docs/development.md) for test and release commands. The
original batch checklist is preserved in [roadmap-history.md](roadmap-history.md);
the full product specification remains in [CLAYFIELD-handoff.md](CLAYFIELD-handoff.md).
