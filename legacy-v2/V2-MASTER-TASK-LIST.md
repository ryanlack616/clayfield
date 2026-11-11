# ClayField V2 Master Task List

This is the canonical day-to-day build board for ClayField V2.

Use this file to decide what to build next. Use
[V2-MASTER-PLAN.md](V2-MASTER-PLAN.md) for the complete specification,
architecture decisions, risks, and release criteria.

## How To Update

After every implementation pass:

1. Check off only tasks that are implemented and tested.
2. Add one sentence to the batch's **Latest update**.
3. Set one concrete **Next task**.
4. Do not close a batch until its **Gate** passes.
5. Record environment blockers instead of marking them complete.

Status values:

- `[x]` complete and verified.
- `[~]` partially complete or usable but not release-complete.
- `[ ]` not complete.
- `[!]` release blocker or unresolved decision.

Current verification:

```text
V1 baseline: 111 passed, 7 skipped
Current suite: 179 passed, 7 skipped
Application self-test: passed
Clean wheel installation/import: passed
```

---

## Batch 0: Baseline and Contracts

Status: `[~]`

Purpose: protect the working V1 application and freeze the semantics that V2
must preserve.

Latest update: The V1 baseline, backup checksum, numerical field contracts,
physical conventions, and headless smoke path are established.

Next task: validate the V1 archive contents and record a clean restore path.

### Tasks

- [x] Confirm the V1 virtual environment and dependencies.
- [x] Record the V1 baseline test result.
- [x] Record `clayfield-v1.7z` and its SHA-256.
- [ ] Validate the archive with `7z t` or an equivalent tool.
- [ ] Record a clean-machine restore procedure.
- [ ] Decide branch, tag, or worktree strategy for V2.
- [x] Define normalized field dtype and bounds.
- [x] Define mesh sample coordinates and image alignment.
- [x] Define procedural frequency units.
- [x] Define tileable sampling rules.
- [x] Define processing stage order.
- [x] Define positive and negative relief semantics.
- [x] Define auto and fixed-range normalization.
- [ ] Define cross-platform numerical tolerances.
- [ ] Define dependency-version compatibility policy.
- [x] Define preview/export resource limits.
- [x] Define the 100 x 100 mm acceptance specimen.
- [x] Build the headless field-to-mesh smoke path.

### Gate

- V1 can be restored independently.
- The archive contents are verified.
- Numerical and physical contracts are documented.
- The smoke path produces a validated closed solid.

---

## Batch 1: Deterministic Field Engine

Status: `[x]` feature-complete, hardening remains.

Purpose: generate native mathematical fields without Qt, images, ComfyUI, or
mesh-specific logic.

Latest update: Noise, tileable noise, waves, Mandelbrot, metadata, bounds,
determinism, and cancellation checkpoints are implemented.

Next task: add cross-platform numerical tolerance fixtures.

### Tasks

- [x] Add immutable normalized-field validation.
- [x] Add field metadata and algorithm identifiers.
- [x] Implement deterministic multiscale noise.
- [x] Implement persistence and lacunarity.
- [x] Implement tileable noise boundaries.
- [x] Implement planar wave interference.
- [x] Implement radial wave interference.
- [x] Implement smooth Mandelbrot fields.
- [x] Bound generator dimensions and iteration counts.
- [x] Add parameter validation.
- [x] Add seed and resolution determinism tests.
- [x] Add generator fixtures and invariants.
- [x] Add procedural-to-mesh tests.
- [x] Add cancellation inside long generator loops.
- [ ] Add cross-platform numerical tolerance fixtures.

### Gate

- All three native generators are reproducible and bounded.
- Generator tests run headlessly.
- Long generator work responds to cancellation.

---

## Batch 2: Unified Pipeline and Fabrication

Status: `[~]` feature-complete, physical calibration remains.

Purpose: route image and procedural sources through one field pipeline and
produce physically meaningful fabrication diagnostics.

Latest update: Image-primary composition now uses the V2 pipeline when
composition is enabled. Processing, masks, mapping, export, final-resolution
analysis, generic profiles, and profile persistence are implemented.

Next task: complete physical calibration artifacts and inspect prints when
hardware is available.

### Tasks

- [x] Convert image input to a normalized V2 primary field.
- [x] Add source resampling.
- [x] Add levels, gamma, curves, brightness, and contrast.
- [x] Add blur, sharpen, threshold, and range policies.
- [x] Add add, subtract, multiply, minimum, maximum, and blend operations.
- [x] Add secondary fields and radial masks.
- [x] Add physical mapping, curves, clamp, scale, offset, inversion, and edge
  falloff.
- [x] Add image-primary secondary-field composition.
- [x] Add image-primary mask composition.
- [x] Add minimum-wall analysis.
- [x] Add resolved-feature analysis.
- [x] Add slope analysis.
- [x] Add high-frequency analysis.
- [x] Add generic fabrication profile limits.
- [x] Add final export-resolution analysis.
- [x] Add procedural STL, 3MF, and PNG/TIFF export.
- [x] Add image export analysis using the V1 compatibility path.
- [x] Add minimum-feature, slope, and wall calibration fixtures.
- [x] Persist the selected fabrication profile in projects.
- [ ] Validate calibration fields against physical prints.

### Gate

- Image and procedural sources share composition and mapping semantics.
- Export warnings describe the actual final field.
- Fabrication warnings are clearly advisory unless explicitly blocking.

---

## Batch 3: State, Persistence, and Workers

Status: `[~]` feature-complete, compatibility hardening remains.

Purpose: make every V2 field durable, recoverable, versioned, and safe under
background execution.

Latest update: Schema version 4, migration, recovery, external-field embedding,
algorithm metadata, immutable publication, and stale worker tokens are in place.

Next task: add concurrent replacement fixtures and complete compatibility checks.

### Tasks

- [x] Add source descriptors.
- [x] Add pipeline snapshots.
- [x] Add schema version 4.
- [x] Migrate V1 projects transactionally.
- [x] Add procedural-only projects.
- [x] Add source hashes and provenance.
- [x] Add processing, mapping, fabrication, and import algorithm versions.
- [x] Add autosave and recovery for procedural/external fields.
- [x] Add resolution-aware cache keys.
- [x] Add worker-safe serialized evaluation.
- [x] Add progress callbacks.
- [x] Add cancellation callbacks.
- [x] Add immutable external field publication.
- [x] Add atomic external field replacement.
- [x] Add stale external-import generation tokens.
- [x] Add concurrent read/replacement tests.
- [x] Reject unsupported algorithm compatibility versions with migration guidance.

### Gate

- Projects save, reopen, recover, and reproduce their fields.
- Stale or cancelled workers cannot replace current project state.
- External arrays cannot be mutated through shared worker state.

---

## Batch 4: Product UI and External Sources

Status: `[~]` workflow-complete, final UI refinement remains.

Purpose: provide one understandable desktop workflow for image, procedural,
and imported sources.

Latest update: Source controls, composition, masks, direct heightmap/mask
imports, provenance summary, fabrication metrics, and export preview are
implemented. External images and masks are supported through file import; no
external generation service is part of the desktop workflow.

Next task: consolidate the panels and add richer candidate/provenance display.

### Tasks

- [x] Add image/procedural source selection.
- [x] Add source reset, randomize, and pattern presets.
- [x] Add noise, wave, and Mandelbrot controls.
- [x] Add background procedural previews.
- [x] Add procedural STL, 3MF, and heightmap export.
- [x] Add secondary-field controls.
- [x] Add blend operation and amount controls.
- [x] Add radial mask controls.
- [x] Add direct secondary heightmap import.
- [x] Add direct mask import.
- [x] Support externally generated heightmaps and masks through import.
- [x] Add source/provenance summary.
- [x] Add Copy Primary Source composition action.
- [x] Add deterministic V2 sample-project/artifact generator.
- [x] Add source-switch data retention.
- [x] Add image-primary secondary-field tests.
- [x] Add image-primary mask tests.
- [x] Add image-primary imported-field tests.
- [x] Add export-resolution metrics to export preview.
- [ ] Consolidate panels into Source, Compose, Process, Height, Fabricate, and
  Export sections.

### Gate

- Image and procedural users can complete the same source/compose/export path.
- Users can identify every primary, secondary, mask, and external source.
- Source changes do not silently discard data.

---

## Batch 5: Release Hardening and Validation

Status: `[~]` local hardening complete, environment validation remains.

Purpose: prove that V2 is installable, performant, slicer-compatible, and ready
for release.

Latest update: `177 passed, 7 skipped`, self-test passes, the wheel builds, a
clean temporary environment imports the wheel, and full 1024² validation memory
is conservatively guarded after observing approximately 3.5 GiB peak RSS.

Next task: run the available live-service, slicer, bundle, and platform checks.

### Tasks

- [x] Run the complete unit/UI regression suite.
- [x] Run application self-test.
- [x] Build a wheel.
- [x] Install/import the wheel in a clean temporary environment.
- [x] Run 1024² mesh benchmark and record peak RSS.
- [x] Run stress tests for large fields and cancellation.
- [x] Generate deterministic V2 sample projects and calibration artifacts.
- [~] Run 512² and 1024² procedural profile history.
- [~] Run GPU/CPU agreement tests on all available drivers.
- [x] Run stress tests for large fields and cancellation.
- [x] Run migration tests across representative V1 projects.
- [x] Run local STL/3MF validation for native fields.
- [x] Run local STL/3MF validation for image-primary fields.
- [x] Run local STL/3MF validation for composed fields.
- [x] Run local STL/3MF validation for imported fields.
- [x] Run local STL/3MF validation for externally imported fields.
- [ ] Run PrusaSlicer digital QA.
- [ ] Validate `clayfield-v1.7z` contents.
- [ ] Test clean-machine restore.
- [x] Build and test the PyInstaller bundle.
- [x] Run packaged self-test.
- [x] Run packaged OpenGL self-test.
- [ ] Test additional Ubuntu versions and GPU drivers.
- [ ] Perform physical print/calibration validation.
- [ ] Define final V2 application/project version policy.
- [ ] Write the V2 acceptance report.
- [ ] Update changelog and release notes.
- [~] Release `2.0.0` after remaining external validation closes.

Pattern expansion after V2:

The full native pattern roadmap is maintained in
[V2-PATTERN-SOURCES-PLAN.md](V2-PATTERN-SOURCES-PLAN.md). The first expansion
batch begins with Voronoi/Worley, ridged noise, domain-warped noise, and SDF
geometric sources. Their native core implementations are now present; these
patterns are not V2.0 release blockers.

### Gate

- Clean installation succeeds.
- Representative projects reopen and reproduce their fields.
- All representative output classes pass mesh and slicer validation.
- P0 blockers are closed.
- Environment-dependent exceptions are documented and approved.

---

## Current Release Blockers

- Archive contents are not validated because no 7-Zip-compatible tool is
  installed.
- Live ComfyUI validation is not run because `CLAYFIELD_COMFYUI_URL` is unset.
- PrusaSlicer validation is not run because `CLAYFIELD_PRUSA_SLICER` is unset.
- Bundle validation is complete locally; additional platform validation remains.
- Additional OS/GPU validation is unavailable.
- Physical print validation is unavailable without a printer.

---

## Current Open-Task Checklist

This is the single checklist for unfinished work. Do not infer completion from
code presence; close each item only after its listed evidence exists.

### Local Code and Documentation

- [x] Add collapsible Compose workflow section.
- [~] Consolidate the visible desktop workflow into Source, Compose, Process,
  Height, Fabricate, and Export groups.
- [x] Add concurrent external-field replacement fixtures.
- [ ] Add cross-platform numerical tolerance fixtures on a second platform.
- [x] Add unsupported compatibility-version migration guidance tests.
- [x] Persist and expose selected fabrication-profile explanations.
- [~] Add physical-calibration artifact generation for feature width, slope, and
  wall thickness.
- [~] Finish remaining advanced pattern controls and presets.
- [~] Add richer streamline, erosion, Penrose, and Truchet controls.
- [~] Update the V2 changelog entry and final acceptance report.

### Environment Validation

- [ ] Validate `clayfield-v1.7z` contents.
- [ ] Test clean-machine restore.
- [ ] Run PrusaSlicer QA with `CLAYFIELD_PRUSA_SLICER`.
- [ ] Run native-field STL/3MF QA.
- [ ] Run image-primary STL/3MF QA.
- [ ] Run composed-field STL/3MF QA.
- [ ] Run imported-field STL/3MF QA.
- [x] Run externally imported-field export tests locally.
- [x] Build and test the PyInstaller bundle.
- [x] Run packaged self-tests.
- [x] Run packaged OpenGL self-test.
- [ ] Test additional Ubuntu versions and GPU drivers.
- [ ] Perform physical print and calibration validation.

### Final Release

- [ ] Review every P0 release blocker in `V2-MASTER-PLAN.md`.
- [x] Produce deterministic V2 sample projects and exports in `dist/v2-samples`.
- [x] Confirm project migration tests from the V1 schema family.
- [x] Confirm wheel installation instructions.
- [x] Write the final V2 acceptance report.
- [x] Update release notes and changelog.
- [~] Tag/release `2.0.0` only after the environment checklist is closed or
  explicitly accepted as a release exception.

---

## Detailed Implementation Instructions

This section is the operating procedure for each batch. A task is not complete
because code exists; it is complete when the implementation, persistence,
tests, and gate evidence all exist.

### Batch 0 Instructions: Baseline and Contracts

1. Work from the archived V1 baseline, not an unverified modified directory.
2. Run the baseline suite before changing code:

   ```sh
   .venv/bin/python -m pytest -q
   ```

3. Record the result, Python version, platform, GPU environment, and optional
   tools present.
4. Validate `clayfield-v1.7z` with a 7-Zip-compatible tool and record the
   command result next to the checksum.
5. Keep numerical contracts in `V2-MASTER-PLAN.md`, not only in source comments.
6. Add a focused test whenever a coordinate, range, frequency, or mapping rule
   changes.
7. Do not change the V1 compatibility path while closing Batch 0.

Batch 0 evidence:

- Baseline test output.
- Backup checksum and archive test output.
- Coordinate/mapping examples.
- Headless field-to-mesh result.

### Batch 1 Instructions: Generator Sources

For every generator:

1. Add an immutable parameter dataclass.
2. Validate bounds before allocating large arrays.
3. Generate normalized `float32` output.
4. Attach `source_type`, `algorithm`, `algorithm_version`, and seed metadata.
5. Add a cancellation check inside every long loop.
6. Add deterministic same-seed and changed-seed tests.
7. Add a small reference fixture with shape, min, max, mean, and sample values.
8. Test the source at preview and export resolutions.
9. Test physical mapping and mesh validation.
10. Add the source to the workflow registry and project descriptor validation.

Required commands:

```sh
.venv/bin/python -m pytest -q tests/test_field_generators.py
.venv/bin/python -m pytest -q tests/test_field_persistence.py
```

Do not add a UI control until the headless generator contract passes.

### Batch 2 Instructions: Pipeline and Fabrication

1. Keep the normalized field as the authoritative composition input.
2. Apply stages in the documented order.
3. Make every range change explicit: clip, normalize, or fixed-range.
4. Route both image and procedural sources through the same V2 path when V2
   composition is enabled.
5. Keep unchanged V1 image projects on compatibility behavior until migration
   tests prove equivalence.
6. Run fabrication analysis on the final export-resolution field, not only the
   preview field.
7. Keep generic warnings advisory unless a real physical constraint is violated.
8. Add synthetic calibration fields for feature width, slope, wall thickness,
   and high-frequency behavior.
9. Verify STL/3MF output after every geometry or mapping change.

Required commands:

```sh
.venv/bin/python -m pytest -q tests/test_field_composition.py tests/test_fabrication.py
.venv/bin/python -m pytest -q tests/test_mesh.py tests/test_export.py tests/test_workers.py
```

### Batch 3 Instructions: State and Workers

1. Persist parameters and provenance, not only cached arrays.
2. Version every output-affecting stage.
3. Reject unsupported algorithm versions with an actionable migration error.
4. Copy and mark imported arrays read-only before publishing them to state.
5. Replace external fields atomically after successful validation.
6. Capture project revision and source hash when starting a worker.
7. Ignore results whose revision, source hash, or generation token is stale.
8. Test cancellation before, during, and after each long stage.
9. Test autosave/recovery for image, procedural, and external-field projects.
10. Test malformed projects transactionally so the active project is unchanged.

Required commands:

```sh
.venv/bin/python -m pytest -q tests/test_project.py tests/test_project_validation.py
.venv/bin/python -m pytest -q tests/test_workers.py tests/test_field_persistence.py
```

### Batch 4 Instructions: Desktop Workflow

1. Make the primary source visible at all times.
2. Group controls into Source, Compose, Process, Height, Fabricate, and Export.
3. Keep external API tools out of the core V2 workflow when file import is
   sufficient.
4. Make imported heightmaps and masks explicit secondary sources.
5. Show source provenance and embedded/external reproducibility status.
6. Ensure source switches retain or explicitly replace prior data.
7. Keep all long generation, import, analysis, and export work in workers.
8. Test UI source switching, save/load, undo/redo, export, and stale results.
9. Test image-primary and procedural-primary composition separately.

Required commands:

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_ui_workflow.py
```

### Batch 5 Instructions: External Sources

The V2 desktop workflow should prefer this path:

```text
External generator or ComfyUI
→ export PNG/TIFF
→ Import Secondary Heightmap or Import Mask
→ deterministic ClayField processing
```

The optional API adapter must remain isolated from the core UI and must:

1. Restrict endpoints to loopback unless remote access is explicitly enabled.
2. Validate API-format workflow JSON.
3. Apply request generation tokens.
4. Enforce response-size and output-count limits.
5. Preserve complete workflow and output provenance.
6. Upload inputs only through the local ComfyUI input boundary.
7. Let users choose output index and role.
8. Reject malformed, stale, or undecodable outputs.
9. Preserve original output bytes alongside normalized fields.
10. Remain optional when ComfyUI is unavailable.

Required commands when a local server is available:

```sh
CLAYFIELD_COMFYUI_URL=http://127.0.0.1:8188 .venv/bin/python -m pytest -q tests/test_comfyui.py
```

### Batch 6 Instructions: Release Hardening

1. Run the complete suite and record the exact result.
2. Run the application self-test and OpenGL self-test where available.
3. Build a wheel and install it into a fresh temporary environment.
4. Build the PyInstaller bundle when the dependency is available.
5. Run native, image, composed, imported, and external-source export checks.
6. Run PrusaSlicer checks when configured.
7. Run live ComfyUI checks when configured.
8. Validate the V1 archive and clean restore procedure.
9. Run benchmarks at 512² and 1024² and record peak RSS.
10. Produce deterministic sample projects and artifacts.
11. Perform physical calibration/print checks when hardware is available.
12. Close only verified tasks; record unavailable environment checks as blocked.
13. Write the acceptance report before changing the release version.
14. Release `2.0.0` only after P0 blockers are closed.

### Pattern Source Instructions

Pattern expansion is tracked separately in
[V2-PATTERN-SOURCES-PLAN.md](V2-PATTERN-SOURCES-PLAN.md).

For each new pattern:

1. Add a parameter dataclass.
2. Define normalized domain and tileability behavior.
3. Add deterministic seed and resolution tests.
4. Add cancellation for long loops.
5. Add source descriptor and algorithm version.
6. Add workflow evaluation support.
7. Add physical mapping and mesh tests.
8. Add minimum-feature and slope warning tests.
9. Add a project round-trip test.
10. Add UI controls only after the headless path passes.

Recommended pattern order:

```text
Voronoi/Worley
→ ridged noise
→ domain-warped noise
→ SDF primitives/Booleans
→ Chladni
→ spectral fields
→ reaction-diffusion
→ phyllotaxis
→ cellular automata
→ L-system branching
→ crack growth
→ flow fields
→ contours
→ erosion
→ Penrose/Truchet refinement

---

## Remaining Work Batches

These are the final dependency-ordered batches. Each batch has a gate and should
be updated after every implementation pass.

### Completion Batch 1: Product Polish and Pattern Refinement

Status: `[~]`

- [ ] Consolidate the visible workflow into Source, Compose, Process, Height,
  Fabricate, and Export sections.
- [ ] Add source/pattern presets.
- [ ] Add richer pattern help text and tooltips.
- [ ] Add true geometric Penrose tiling.
- [ ] Add richer Truchet arc geometry.
- [ ] Add advanced streamline controls.
- [ ] Improve hydraulic erosion controls and workload feedback.
- [ ] Add advanced crack-growth controls.
- [ ] Add material-specific fabrication profile placeholders.
- [ ] Add UI tests for every visible pattern source.

Gate: users can select, configure, preview, reset, randomize, save, and export
every supported pattern source without editing project files.

### Completion Batch 2: Local Hardening

Status: `[~]`

- [ ] Add cross-platform numerical fixtures on a second platform.
- [ ] Run 512² and 1024² profiling history.
- [ ] Run large-field stress and cancellation tests.
- [ ] Run representative migration tests.
- [ ] Run native, image, composed, and imported STL/3MF validation.
- [ ] Produce and inspect digital calibration artifacts.
- [ ] Update release notes and changelog.

Gate: the current platform can reproduce, validate, and export representative
V2 projects within documented resource limits.

### Completion Batch 3: External Validation

Status: `[ ]` blocked by external tools and hardware.

- [ ] Validate the V1 archive contents.
- [ ] Test clean-machine restore.
- [ ] Build and test the PyInstaller bundle.
- [ ] Run packaged self-tests.
- [ ] Run packaged OpenGL self-test.
- [ ] Run PrusaSlicer QA.
- [ ] Test additional Ubuntu versions and GPU drivers.
- [ ] Perform physical feature, slope, and wall calibration prints.

Gate: every unavailable external check is completed or explicitly accepted as a
documented release exception.

### Completion Batch 4: V2 Release

Status: `[ ]` waiting for Batches 1-3.

- [ ] Write the final acceptance report.
- [ ] Confirm all P0 blockers are closed.
- [ ] Confirm the wheel and bundle installation instructions.
- [ ] Produce final sample projects and export artifacts.
- [ ] Define final application/project version policy.
- [ ] Tag/release `2.0.0`.

Gate: V2 is installable, reproducible, validated, documented, and ready for
users.
```
