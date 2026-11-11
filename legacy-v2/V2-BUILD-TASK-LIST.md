# ClayField V2 Build Task List

This is the practical execution checklist for building ClayField V2. The
product specification and risk register are in
[V2-MASTER-PLAN.md](V2-MASTER-PLAN.md); this file is the shorter build board.

Build batches are dependency boundaries. Do not start the next batch until the
current batch gate passes. A batch may contain multiple implementation passes,
but every pass must leave the application testable.

Status:

- `[x]` complete and verified.
- `[~]` partially complete or usable but not release-complete.
- `[ ]` not built.
- `[!]` release blocker or unresolved decision.

## Current Build Snapshot

Current verification:

```text
V1 baseline: 111 passed, 7 skipped
Current suite: 179 passed, 7 skipped
Application self-test: passed
```

Latest completed slice:

- Image-primary composition now uses the V2 field pipeline when secondary or
  mask composition is enabled.
- External heightmap and mask fields are copied, validated, published
  read-only, and persisted with original bytes when available.
- External-import workers use generation tokens and reject stale results when
  the source or project changes.
- Final export-resolution fabrication analysis is shown asynchronously for
  procedural, composed, and legacy image exports.
- Generic fabrication-profile limits and source/provenance summary UI are
  implemented at the core boundary.
- The current wheel builds successfully and `clayfield --self-test` passes.
- A clean temporary environment installs the wheel and imports ClayField 0.3.0.
- The local 1024² construction benchmark is fast, but full validation can peak
  around 3.5 GiB; the exporter uses a conservative 20x safety estimate.

Next build target:

```text
Slicer and performance QA
→ clean install/recovery validation
→ clean install/recovery validation
→ physical calibration when hardware is available
→ V2.0.0 release
```

---

## Batch 0: Baseline and Contracts

Goal: protect V1 and make V2 semantics unambiguous.

Status: `[~]` Baseline is established, but archive-content validation, clean
restore instructions, and cross-platform tolerance decisions remain open.

Batch update: The V1 environment is working and the original baseline passed
`111 passed, 7 skipped`. The current V2 suite passes `179 passed, 7 skipped`.
The backup checksum is recorded, but the archive still needs an actual contents
test with a 7-Zip-compatible tool.

Next build target: close the archive/restore tasks and write the numerical
tolerance policy before changing core semantics.

Gate state: not closed.

### Tasks

- [x] Confirm the V1 virtual environment and dependency imports.
- [x] Run and record the V1 baseline test result.
- [x] Record the V1 backup filename and SHA-256.
- [ ] Validate the 7-Zip archive contents with `7z t` or an equivalent tool.
- [ ] Record a clean-machine restore procedure.
- [ ] Decide the V2 branch, tag, or worktree strategy.
- [x] Define normalized field dtype and bounds.
- [x] Define mesh sample coordinates and image-to-mesh alignment.
- [x] Define procedural frequency units.
- [x] Define tileable sampling semantics.
- [x] Define processing stage order.
- [x] Define positive and negative relief semantics.
- [x] Define auto versus fixed normalization.
- [ ] Define supported numerical tolerances across platforms.
- [ ] Define dependency-version compatibility policy.
- [x] Define preview and export resource limits.
- [x] Define the 100 x 100 mm acceptance specimen.
- [x] Build the headless field-to-mesh smoke path.

### Gate

- V1 can be restored independently.
- V1 tests pass in a recorded environment.
- The 7-Zip backup is proven recoverable.
- Numerical and physical contracts are written down.
- A small deterministic field becomes a validated closed solid.

---

## Batch 1: Deterministic Field Engine

Goal: build native procedural sources without Qt, external services, or mesh code.

Status: `[x]` Native source generation is complete for the current V2 scope.

Batch update: Multiscale noise, tileable noise, planar/radial waves, Mandelbrot,
metadata, deterministic fixtures, and procedural-to-mesh tests are implemented.
The remaining unchecked items are hardening tasks for granular cancellation and
cross-platform tolerance, not missing generator types.

Next build target: add cancellation checkpoints and freeze the numerical golden
fixtures before release profiling.

Gate state: closed for feature construction; hardening remains.

### Tasks

- [x] Add immutable normalized-field validation.
- [x] Add field metadata and coordinate contracts.
- [x] Add source descriptors and algorithm identifiers.
- [x] Implement deterministic multiscale noise.
- [x] Implement persistence and lacunarity.
- [x] Implement tileable noise boundaries.
- [x] Implement planar wave interference.
- [x] Implement radial wave interference.
- [x] Implement smooth Mandelbrot escape-time fields.
- [x] Bound generator dimensions and iterations.
- [x] Add parameter validation.
- [x] Add seed and resolution determinism tests.
- [x] Add generator golden/invariant fixtures.
- [x] Add procedural-to-mesh tests.
- [ ] Add granular cancellation inside long generator loops.
- [ ] Add cross-platform numerical tolerance fixtures.

### Gate

- Noise, waves, and Mandelbrot work without an image.
- Same source snapshot and seed reproduce the same field.
- Fields are finite, bounded, and valid at preview/export resolutions.
- Generator tests run headlessly.

---

## Batch 2: Pipeline and Fabrication Core

Goal: turn sources into one authoritative field and validated physical solid.

Status: `[~]` Core pipeline and final-resolution analysis are working; release-
grade fabrication profiles and calibration are not yet complete.

Batch update: Processing, composition, masks, mapping, physical fields,
procedural exports, legacy image exports, wall metrics, slope metrics,
high-frequency warnings, and final export-resolution preview analysis are
implemented and tested. Fabrication profiles and calibration support remain.

Next build target: add deterministic feature/slope/wall calibration fixtures and
generic fabrication-profile support.

Gate state: feature gate closed; release gate open.

### Tasks

- [x] Add explicit source resampling.
- [x] Add levels and gamma processing.
- [x] Add curves processing.
- [x] Add brightness and contrast processing.
- [x] Add blur and sharpen processing.
- [x] Add threshold processing.
- [x] Add explicit clip and auto-normalize policies.
- [x] Add add, subtract, multiply, minimum, maximum, and blend operations.
- [x] Add radial masks.
- [x] Add secondary-field composition.
- [x] Add mapping curves, clamp, scale, offset, and inversion.
- [x] Add edge falloff.
- [x] Add normalized-to-physical mapping.
- [x] Add physical pipeline result object.
- [x] Add minimum wall metrics.
- [x] Add sampled feature-width estimates.
- [x] Add slope estimates.
- [x] Add high-frequency heuristics.
- [x] Add blocking versus advisory warnings.
- [x] Add procedural STL export.
- [x] Add procedural 3MF export.
- [x] Add procedural PNG/TIFF export.
- [x] Add final export-resolution fabrication analysis before confirmation.
- [x] Add generic fabrication profile schema.
- [x] Add minimum-feature calibration fixture.
- [x] Add slope calibration fixture.
- [x] Add wall-thickness calibration fixture.

### Gate

- A composed field maps to a correctly dimensioned physical surface.
- A 100 x 100 mm panel with a 3 mm base and 5 mm relief validates.
- STL and 3MF output is watertight and slicer-compatible.
- Warnings describe the actual export field.

---

## Batch 3: State, Persistence, and Workers

Goal: make V2 fields durable, recoverable, and safe under background execution.

Status: `[~]` Persistence and worker infrastructure are complete for the current
schema; algorithm-version metadata and concurrency fixtures remain.

Batch update: Schema version 4, procedural projects, V1 migration, recovery,
cache keys, external-field embedding, immutable publication, generation tokens,
progress, and cancellation callbacks are implemented. Remaining concerns are
complete algorithm-version metadata and concurrent replacement fixtures.

Next build target: version every output-affecting pipeline stage and add
concurrency fixtures.

Gate state: feature gate closed; release gate open.

### Tasks

- [x] Add source descriptors.
- [x] Add pipeline snapshots.
- [x] Add schema version 4.
- [x] Migrate V1 projects transactionally.
- [x] Add procedural-only projects.
- [x] Add source hashes and algorithm metadata.
- [x] Add procedural autosave and recovery.
- [x] Add stable resolution-aware cache keys.
- [x] Add worker-safe serialized evaluation.
- [x] Add progress callbacks.
- [x] Add cancellation callbacks.
- [x] Add external secondary-field embedding.
- [x] Add embedded mask-field persistence.
- [x] Add complete processing, mapping, fabrication, and import algorithm
  version metadata.
- [x] Make imported arrays read-only after publication.
- [x] Publish imported arrays atomically.
- [ ] Add concurrent replacement tests.
- [x] Add stale-result tokens to current ComfyUI and external-import workers.

### Gate

- A procedural project saves, reloads, and reproduces its field.
- Existing V1 projects migrate without unintended changes.
- Recovery handles procedural and external fields.
- Cancelled or stale workers cannot replace current state.

---

## Batch 4: User Workflow and Fabrication UI

Goal: expose the complete pipeline without breaking the existing image workflow.

Status: `[~]` Procedural and composition UI is usable, and image-primary
composition now shares the V2 field pipeline; release-facing UI work remains.

Batch update: Source selection, procedural controls, image/procedural
composition, masks, direct heightmap/mask imports, fabrication metrics, export
preview warnings, and procedural export are implemented. Remaining work is
final-resolution analysis, image-primary mask/ComfyUI coverage, provenance UI,
source-switch safety, and panel consolidation.

Next build target: calculate warnings from the actual export field, then add the
source/provenance summary and consolidate panels into Source, Compose, Process,
Height, Fabricate, and Export sections.

Gate state: feature gate closed; release gate open for final UI and analysis.

### Tasks

- [x] Add image/procedural source selector.
- [x] Add noise controls.
- [x] Add wave controls.
- [x] Add Mandelbrot controls.
- [x] Add background procedural preview generation.
- [x] Add procedural heightmap preview.
- [x] Add procedural STL/3MF export.
- [x] Add procedural heightmap export.
- [x] Add secondary-field enable/disable control.
- [x] Add secondary source selector.
- [x] Add secondary source controls.
- [x] Add composition operation and amount controls.
- [x] Add radial mask controls.
- [x] Add direct secondary heightmap import.
- [x] Add direct mask import.
- [x] Add fabrication metrics to the terrain panel.
- [x] Add warning data to export preview.
- [x] Persist composition and mask settings through undo/redo.
- [x] Persist imported fields through projects.
- [x] Route image-primary and procedural-primary sources through one unified
  composition pipeline.
- [x] Add image-primary secondary-field tests.
- [x] Add image-primary mask tests.
- [x] Add image-primary ComfyUI-result tests.
- [x] Add final export-resolution warning display.
- [x] Add explicit source/provenance summary UI.
- [x] Add source-switch data-retention behavior.
- [ ] Consolidate panels into Source, Compose, Process, Height, Fabricate, and
  Export sections.

### Gate

- Image users and procedural users share the same field semantics.
- Secondary and mask fields work for both source types.
- Fabrication warnings are visible before export.
- Source changes do not silently discard work.

---

## Batch 5: External Image Interchange

Goal: support heightmaps and masks produced by any external image tool without
adding an external service dependency.

Status: `[x]` External heightmap and mask interchange is complete.

Batch update: External heightmap/mask import, validation, provenance, original
artifact preservation, project embedding, composition, and export are
implemented.

Next build target: begin Batch 6 release hardening.

Gate state: closed for core V2.

### Tasks

- [x] Add direct heightmap/mask interchange.
- [x] Validate imported fields and preserve original bytes.
- [x] Persist imported sources and composition settings.
- [x] Export imported fields through the normal pipeline.

### Gate

- External output cannot replace a mathematical source silently.
- Imported fields remain local and provenance-preserving.
- Imported fields work without network services.

---

## Batch 6: Production Hardening and Release

Goal: prove, package, and release V2.

Status: `[ ]` Not started.

Batch update: The release checklist is defined but no V2 release-candidate
hardening pass has been accepted yet. Existing local tests and self-tests are
green, but final-resolution profiling, slicer QA across all source classes,
physical calibration, clean-machine install, and release versioning remain.

Next build target: close the Batch 0 blockers, then complete the unified field
pipeline and external provenance blockers before beginning release hardening.

Gate state: not started.

### Tasks

- [ ] Profile 512 x 512 generation.
- [ ] Profile 1024 x 1024 generation.
- [ ] Profile composed-field export.
- [ ] Measure peak memory.
- [ ] Test large-workload cancellation.
- [ ] Test stale-result rejection under rapid edits.
- [ ] Run the complete unit and UI suite.
- [ ] Run GPU/CPU agreement tests.
- [ ] Run stress tests.
- [ ] Run migration tests.
- [ ] Run STL/3MF validation for native generators.
- [ ] Run STL/3MF validation for composed fields.
- [ ] Run STL/3MF validation for imported fields.
- [ ] Run STL/3MF validation for ComfyUI-derived fields.
- [ ] Run PrusaSlicer digital QA.
- [ ] Run optional live ComfyUI QA.
- [ ] Validate the V1 archive contents.
- [ ] Test clean-machine restore.
- [x] Test fresh wheel installation.
- [x] Test fresh bundle installation.
- [x] Run packaged self-test.
- [x] Run packaged OpenGL self-test.
- [x] Produce deterministic sample projects.
- [x] Produce representative STL, 3MF, and heightmap artifacts.
- [ ] Perform physical print/calibration validation when hardware is available.
- [x] Define V2 application and project version policy.
- [x] Write the V2 acceptance report.
- [x] Update changelog and release notes.
- [~] Release `2.0.0` after remaining external validation closes.

### Gate

- Clean installation succeeds.
- Representative projects reopen and reproduce their fields.
- Native, composed, imported, and ComfyUI-derived outputs slice correctly.
- All P0 release blockers are closed.
- No P1 task remains without an explicit documented exception.

---

## Critical Path

The shortest safe build order for the remaining work is:

```text
Unified image/procedural pipeline
→ external worker generation tokens
→ complete workflow/artifact provenance
→ final export-resolution analysis
→ ComfyUI upload and output selection
→ source/provenance UI
→ performance and slicer QA
→ clean release validation
→ V2.0.0
```

Do not spend time on the optional ComfyUI CLI adapter, advanced generators,
adaptive meshes, ceramic compensation, or a general node editor before this
critical path is complete.
