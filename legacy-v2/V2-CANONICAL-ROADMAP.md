# ClayField V2 Canonical Completion Roadmap

This is the one file to follow for finishing ClayField V2.

The other documents contain supporting detail, historical requirements, or user
instructions, but this file is the execution authority. Update this file after
every build pass.

Current verification:

```text
V1 baseline: 111 passed, 7 skipped
Current suite: 179 passed, 7 skipped
Application self-test: passed
Clean wheel installation/import: passed
```

Status:

- `[x]` implemented and verified.
- `[~]` partially complete or locally usable but not release-complete.
- `[ ]` not complete.
- `[!]` release blocker or environment-dependent.

## Update Rules

After each implementation pass:

1. Check only tasks supported by code and tests.
2. Add one sentence to the batch's **Latest update**.
3. Set one concrete **Next task**.
4. Do not close a batch until its gate passes.
5. Record unavailable tools or hardware as blockers, never as passes.

## Batch Order

```text
Batch 0: Baseline and contracts
        ↓
Batch 1: Native field and pattern engine
        ↓
Batch 2: Unified pipeline and fabrication
        ↓
Batch 3: Persistence and worker safety
        ↓
Batch 4: Product UI and external file interchange
        ↓
Batch 5: Local hardening and release validation
```

---

## Batch 0: Baseline and Contracts

Status: `[x]` local baseline/contract gate closed; external platform validation
remains separate.

Purpose: protect V1 and freeze the semantics that V2 must preserve.

Latest update: The V1 baseline, backup checksum, archive integrity test,
restore procedure, numerical policy, physical conventions, and headless smoke
path are established.

Next task: apply the same policy on a clean machine/platform.

### Tasks

- [x] Confirm Python environment and project dependencies.
- [x] Run the V1 baseline suite.
- [x] Record `clayfield-v1.7z` SHA-256.
- [x] Validate archive contents with a 7-Zip-compatible Python tool.
- [x] Record the clean-machine restore procedure.
- [x] Decide to keep V2 in the active working tree while preserving the V1
  archive as the rollback baseline.
- [x] Define normalized field dtype and bounds.
- [x] Define mesh sample coordinates and image alignment.
- [x] Define procedural frequency units.
- [x] Define tileable sampling rules.
- [x] Define processing stage order.
- [x] Define positive/negative relief semantics.
- [x] Define auto/fixed normalization.
- [x] Define cross-platform numerical tolerances.
- [x] Define dependency-version compatibility policy.
- [x] Define preview/export resource limits.
- [x] Define the 100 x 100 mm acceptance specimen.
- [x] Build the headless field-to-mesh smoke path.

### Gate

- V1 can be restored independently.
- Archive integrity is verified.
- Numerical and physical contracts are documented.
- A deterministic field produces a validated closed solid.

---

## Batch 1: Native Field and Pattern Engine

Status: `[x]` feature-complete; additional tolerance/preset refinement remains.

Purpose: produce deterministic normalized float32 fields without Qt or external
services.

Latest update: Native sources now include terrain, cellular, geometric,
mathematical, organic, flow, erosion, branching, crack, and tiling families.

Next task: add cross-platform reference fixtures and finish source presets.

### Source contract tasks

- [x] Add immutable normalized-field validation.
- [x] Add source metadata and algorithm identifiers.
- [x] Add seed and resolution semantics.
- [x] Add cancellation callback support.
- [x] Add deterministic reference statistics.
- [ ] Add reference fixtures on a second supported platform.

### Implemented source families

- [x] Multiscale noise.
- [x] Tileable noise.
- [x] Ridged noise.
- [x] Domain-warped noise.
- [x] Voronoi/Worley.
- [x] Planar and radial waves.
- [x] Mandelbrot.
- [x] SDF circles, rectangles, repetition, and Boolean operations.
- [x] Chladni fields.
- [x] Spectral/Fourier fields.
- [x] Reaction-diffusion.
- [x] Phyllotaxis.
- [x] Cellular automata.
- [x] Flow fields.
- [x] Erosion-style fields.
- [x] L-system branching.
- [x] Crack-growth fields.
- [x] Penrose-style fields.
- [x] Truchet fields.

### Pattern usability tasks

- [x] Add source reset.
- [x] Add source randomization.
- [x] Add common pattern presets.
- [x] Add advanced pattern parameter pages.
- [ ] Add searchable/category-based pattern selection.
- [ ] Add pattern thumbnails or preview swatches.
- [ ] Add pattern-specific help text for every advanced family.
- [ ] Add true geometric Penrose tiling.
- [ ] Add richer Truchet arc geometry.
- [ ] Add richer flow streamlines.
- [ ] Add advanced erosion controls.

### Gate

- Every implemented source is deterministic, bounded, cancellable, persistent,
  physically mappable, and exportable.

---

## Batch 2: Unified Pipeline and Fabrication

Status: `[~]` core complete; quality/profile refinement remains.

Purpose: route image and procedural sources through one normalized field path and
produce physically meaningful fabrication diagnostics.

Latest update: Image-primary composition, secondary fields, masks, final
export-resolution analysis, profiles, and calibration artifact generation are
implemented.

Next task: finish source-editor parity and physical profile calibration.

### Pipeline tasks

- [x] Convert image input to normalized V2 primary field.
- [x] Apply explicit source resampling.
- [x] Apply levels, gamma, curves, contrast, blur, sharpen, and threshold.
- [x] Apply composition operations and masks.
- [x] Apply mapping curves, clamp, scale, offset, inversion, and falloff.
- [x] Preserve the V1 compatibility path for unchanged projects.
- [x] Publish normalized and physical pipeline results.
- [x] Analyze the final export-resolution field before confirmation.

### Fabrication tasks

- [x] Analyze wall thickness.
- [x] Analyze resolved feature width.
- [x] Analyze slope.
- [x] Analyze high-frequency detail.
- [x] Separate advisory and blocking warnings.
- [x] Add generic fabrication profiles.
- [x] Persist selected fabrication profile.
- [x] Generate feature-width calibration panels.
- [x] Generate slope calibration panels.
- [x] Generate wall-thickness calibration panels.
- [ ] Validate calibration panels against physical prints.
- [ ] Add material/printer-specific profile placeholders.

### Mesh validation tasks

- [x] Validate watertightness.
- [x] Validate winding consistency.
- [x] Validate positive volume.
- [x] Validate finite coordinates.
- [x] Validate degenerate faces.
- [x] Validate edge ownership: exactly two faces per edge.
- [x] Validate one connected component.
- [x] Report Euler number.
- [ ] Add a full triangle self-intersection backend or explicit structured-grid
  guarantee.
- [ ] Report self-intersection status clearly when not checked.

### Gate

- Image and procedural sources share composition/mapping semantics.
- Export warnings describe the actual final field.
- Mesh reports closure, manifoldness, connectivity, volume, and degeneracy.

---

## Batch 3: Persistence and Worker Safety

Status: `[~]` feature-complete; compatibility fixtures remain.

Purpose: make projects durable and ensure background operations cannot publish
stale or mutable data.

### Tasks

- [x] Add source descriptors and pipeline snapshots.
- [x] Add schema version 4.
- [x] Migrate V1 projects transactionally.
- [x] Add procedural-only projects.
- [x] Store source hashes and algorithm versions.
- [x] Store processing, mapping, fabrication, and import versions.
- [x] Add autosave and recovery for external fields.
- [x] Add resolution-aware cache keys.
- [x] Add worker progress and cancellation.
- [x] Add immutable external field publication.
- [x] Add atomic external field replacement.
- [x] Add generation tokens for external imports.
- [x] Reject unsupported algorithm compatibility versions.
- [x] Add concurrent replacement coverage.
- [ ] Add full project-layer summary persistence.
- [ ] Add recovery messaging for unavailable original external files.

### Gate

- Projects save, reopen, recover, and reproduce fields.
- Stale/cancelled workers cannot replace current state.
- External arrays cannot be mutated through worker state.

---

## Batch 4: Product UI and External File Interchange

Status: `[~]` workflow-complete; final interaction refinement remains.

Purpose: provide a clear desktop workflow without external generation services.

Latest update: Source/compose/process/height/fabricate/export grouping, direct
heightmap/mask import, provenance, pattern controls, presets, and source safety
are implemented.

Next task: finish full source-editor parity and panel consolidation.

### UI tasks

- [x] Group Source controls.
- [x] Group Compose controls.
- [x] Group Process controls.
- [x] Group Height controls.
- [x] Group Fabricate controls.
- [x] Group Export controls.
- [x] Add primary source selection.
- [x] Add secondary source selection.
- [x] Add mask selection.
- [x] Add source reset/randomize.
- [x] Add pattern presets.
- [x] Add provenance summary.
- [x] Add fabrication profile selector.
- [x] Add final export metrics.
- [x] Add open-top tray/container wall controls.
- [ ] Make primary and secondary SourceEditor controls fully identical.
- [ ] Add searchable pattern categories.
- [ ] Add keyboard focus/order and accessibility labels.
- [ ] Persist panel sizes and collapsed states.

### Interchange tasks

- [x] Import secondary heightmaps.
- [x] Import masks.
- [x] Preserve original imported bytes.
- [x] Persist normalized working fields.
- [x] Compose imported fields with native fields.
- [x] Export imported/composed fields.

### Gate

- Image and procedural users share one understandable path.
- Imported sources are explicit and reproducible from embedded project data.
- No external image-generation service is required by the application.

---

## Batch 5: Local Hardening, Packaging, and Release

Status: `[~]` locally hardened; external validation remains.

Purpose: produce the final local release artifacts and record all unavailable
external checks explicitly.

### Local tasks

- [x] Run full regression suite.
- [x] Run stress tests.
- [x] Run available GPU/CPU agreement tests.
- [x] Run migration tests.
- [x] Run local mesh validation across representative fields.
- [x] Build wheel.
- [x] Install/import wheel in clean temporary environment.
- [x] Build PyInstaller bundle.
- [x] Run packaged self-test.
- [x] Run packaged OpenGL self-test.
- [x] Generate deterministic V2 samples.
- [x] Generate fabrication calibration artifacts.
- [x] Generate SHA-256 release manifest.
- [x] Generate `dist/clayfield-2.0.0-linux-x86_64.tar.gz`.
- [~] Run 512² and 1024² profile history.
- [x] Add current-platform numerical reference fixtures; second-platform
  execution remains open.

### External tasks

- [x] Validate V1 archive contents.
- [x] Document clean-machine restore; execution on a separate machine remains open.
- [ ] Run PrusaSlicer QA.
- [ ] Test additional Ubuntu versions and GPU drivers.
- [ ] Perform physical calibration prints.
- [ ] Inspect representative physical prints.

### Release tasks

- [x] Set application/package version to `2.0.0`.
- [x] Write acceptance report.
- [x] Update changelog/release notes.
- [ ] Close all external P0 blockers or record approved exceptions.
- [ ] Tag/publish final `2.0.0` artifacts.

### Gate

- Local artifacts pass all available checks.
- External limitations are documented.
- Release exceptions are explicitly approved.
- V2.0.0 is not presented as physically validated until prints are inspected.

---

## Post-V2 Backlog

- [ ] Full SDF Boolean composition editor.
- [ ] True Penrose tiling geometry.
- [ ] Rich Truchet arc geometry.
- [ ] Advanced flow streamlines.
- [ ] Advanced hydraulic erosion.
- [ ] Additional crack-growth models.
- [ ] Material-specific fabrication profiles.
- [ ] Adaptive mesh topology.
- [ ] Ceramic shrinkage/firing compensation.
- [ ] Mold-release and draft analysis.
- [ ] General visual node editor.

---

## Phase Verification Order

After the completion batches are closed, verify the numbered product phases in
this order. A phase is re-verified against the current V2 architecture; it is
not a second implementation track.

### Phase 0: Foundation and Recovery

Status: `[~]` local validation complete; clean-machine and second-platform runs remain.

- [x] Python environment and dependency installation.
- [x] V1 baseline test result.
- [x] Archive checksum and integrity test.
- [x] Restore procedure documentation.
- [ ] Clean-machine restore execution.
- [ ] Cross-platform tolerance run.

Gate: baseline restoration is verified on a clean supported target.

### Phase 1: Deterministic Sources

Status: `[x]`

- [x] Native source registry and descriptors.
- [x] Noise, waves, Mandelbrot, cellular, geometric, organic, flow, erosion,
  branching, crack, and tiling source families.
- [x] Determinism, bounds, cancellation, persistence, and export coverage.

Gate: every supported source produces a valid normalized field and export path.

### Phase 2: Unified Field Pipeline

Status: `[x]` core behavior, `[~]` profile/calibration refinement.

- [x] Image-primary and procedural-primary composition.
- [x] Secondary fields and masks.
- [x] Processing and mapping stages.
- [x] Physical mapping and final export analysis.
- [x] Fabrication profile persistence.
- [ ] Physical calibration inspection.

Gate: source types share field, mapping, fabrication, and export semantics.

### Phase 3: Persistence and Worker Safety

Status: `[x]` core behavior, `[~]` cross-platform refinement.

- [x] Schema version 4 and migration.
- [x] Procedural-only projects.
- [x] External field embedding and provenance.
- [x] Recovery and autosave.
- [x] Stale generation tokens and cancellation.
- [x] Algorithm compatibility rejection.
- [ ] Second-platform compatibility run.

Gate: projects and workers remain safe across save, reload, recovery, and source
changes.

### Phase 4: Product Workflow

Status: `[~]`

- [x] Source selection and source-local controls.
- [x] Composition and mask workflow.
- [x] External heightmap/mask import.
- [x] Provenance and fabrication summaries.
- [x] Export preview and final analysis.
- [ ] Final panel consolidation and accessibility pass.

Gate: users can complete the workflow without confusing source, mapping, or
fabrication controls.

### Phase 5: Mesh and Export Reliability

Status: `[x]` local behavior, `[~]` external validation.

- [x] Watertight and edge-ownership validation.
- [x] Winding, volume, connectivity, Euler, and degenerate-face reporting.
- [x] STL, 3MF, and heightmap exports.
- [x] Procedural and composed export regeneration.
- [ ] PrusaSlicer validation.
- [ ] Physical print validation.

Gate: representative outputs are slicer-compatible and physically verified.

### Phase 6: Pattern Expansion

Status: `[~]` core pattern expansion complete; calibration/refinement remains.

- [x] P1 native pattern batch.
- [x] P2/P3/P4 core pattern sources.
- [x] Pattern source persistence and export compatibility.
- [~] Richer pattern presets and help.
- [ ] Pattern-specific physical calibration.

Gate: patterns are usable, documented, and fabrication-aware.

### Phase 7: External File Interchange

Status: `[x]` for core V2.

- [x] Secondary heightmap import.
- [x] Mask import.
- [x] Original artifact preservation.
- [x] Deterministic processing after import.
- [x] Imported-field export.

Gate: external generation is handled through ordinary local files without an
external service dependency.

### Phase 8: Performance and GPU

Status: `[~]`

- [x] CPU-authoritative processing.
- [x] GPU preview agreement on the available environment.
- [x] 1024² benchmark and memory observation.
- [x] Large-field stress coverage.
- [ ] Additional drivers and OS targets.
- [~] Extended 512²/1024² performance history.

Gate: performance and GPU behavior are documented for supported targets.

### Phase 9: Packaging and Installation

Status: `[x]` local package behavior, `[~]` additional targets.

- [x] Wheel build.
- [x] Clean wheel installation/import.
- [x] PyInstaller bundle build.
- [x] Packaged self-test.
- [x] Packaged OpenGL self-test.
- [ ] Additional distribution/OS checks.

Gate: clean users can install and launch the verified package.

### Phase 10: Release

Status: `[~]` locally packaged, externally blocked.

- [x] Version set to `2.0.0`.
- [x] Release archive created.
- [x] Checksums recorded.
- [x] Acceptance report started.
- [ ] Close archive/platform/slicer/physical validation exceptions.
- [ ] Final release approval.

Gate: V2.0.0 is released only after remaining exceptions are completed or
explicitly approved.
- [ ] Cloud or remote generation.
