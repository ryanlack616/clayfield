# ClayField V2 Master Plan

Status: implementation in progress

Target product release: `2.0.0`

Baseline: ClayField `0.3.0`

This document is the implementation authority for the V2 product direction. It
turns the existing image-to-relief application into a deterministic procedural
height-field authoring tool without discarding the working V1 foundation.

The concise execution checklist is
[V2-BUILD-TASK-LIST.md](V2-BUILD-TASK-LIST.md). Use this document for the full
specification, risk register, and acceptance criteria; use the task list to
execute the build batches.

The clean six-batch board for routine updates is
[V2-MASTER-TASK-LIST.md](V2-MASTER-TASK-LIST.md). It is the preferred daily
execution list; this document remains the detailed authority.

The one-file completion roadmap is
[V2-CANONICAL-ROADMAP.md](V2-CANONICAL-ROADMAP.md). It consolidates the current
batch statuses, gates, local verification, external blockers, and post-V2 work.

The post-V2 procedural pattern roadmap is in
[V2-PATTERN-SOURCES-PLAN.md](V2-PATTERN-SOURCES-PLAN.md). Pattern expansion is
separate from the V2.0 release critical path.

The in-app external-generation service integration was removed from the V2
product. External tools may still produce PNG/TIFF heightmaps or masks, which
are imported through ClayField's normal file-import controls. Older ComfyUI API
planning sections below are retained only as historical design context and are
not active V2 implementation requirements.

The plan is intentionally staged. Each phase must leave the application usable,
testable, and releasable before the next phase begins.

Current implementation status:

- The V1 baseline passed in `.venv`: `111 passed, 7 skipped`; the current suite
  passes `179 passed, 7 skipped` after the V2 field, UI, export, and external-import tests were
  added.
- The V1 archive is present and checksummed; archive-content testing still needs
  a 7-Zip-compatible tool.
- Batch 1 has a headless normalized-field contract and deterministic noise,
  wave, and Mandelbrot generators.
- Batch 2 has field composition, ordered processing, normalized-to-physical
  mapping, an authoritative pipeline result, and conservative fabrication
  metrics.
- Batch 3 has serializable source/pipeline descriptors, project schema version
  4, procedural-only save/load, V1 migration, procedural recovery snapshots,
  cache keys, and a worker-safe headless evaluator.
- Batch 4 has procedural source controls, background preview generation, stale
  preview-key separation from export resolution, procedural project loading, and
  procedural heightmap regeneration at export resolution.
- Batch 5 has an optional dependency-free local ComfyUI HTTP client, API-format
  workflow submission, history polling, output download, normalized image
  validation, workflow/output hashes, provenance descriptors, cancellation,
  timeouts, response limits, and mock-server coverage.
- Batch 5 UI integration has workflow selection, local endpoint controls,
  background submission, output validation, secondary-field import, provenance
  persistence, and offline error presentation.
- Full Source/Compose/Process/Height/Fabricate/Export panel consolidation and
  richer ComfyUI mask/file interchange are not implemented yet.

---

## 0. Pre-Build Definition Of Ready

The V2 feature list is not, by itself, sufficient to begin implementation. The
following decisions must be fixed before the first production feature is built.
Otherwise the same field may change meaning as the UI, generator, mesh, and
project format are implemented independently.

### 0.1 Baseline protection

- [ ] Create and verify the archived 0.3.0 backup supplied by the project owner.
- [ ] Record the archive filename, checksum, source revision if available, and
  restore instructions outside the working tree.
- [ ] Run the current full local test suite and preserve the result.
- [ ] Save one representative image project, STL, 3MF, and heightmap fixture.
- [ ] Record the dimensions and slicer results of the representative exports.
- [ ] Decide whether V2 development uses a branch, a tagged baseline, or a
  separate working directory.
- [ ] Do not delete or rewrite the V1 implementation until V2 has a passing
  migration and regression suite.

The archive is a safety net, not a substitute for a reproducible source
baseline. We need both a recoverable backup and a testable code reference.

Current workspace observation: `clayfield-v1.7z` is present and identified as a
7-Zip archive. Its SHA-256 is
`bdf4f23dca1d768f876143d8f0bf4b1e8415cbde3ef94d977a3e8b7d9f2c1f37`. Archive
content testing is still pending because the current environment does not have
the `7z`, `7zz`, `7za`, `bsdtar`, or `unar` command available.

The current system Python also lacks the project dependencies (`cv2`, PySide6,
Trimesh, and others), so the V1 test baseline is not yet established in this
environment. Dependency installation and a clean baseline test run are Phase 0
work, not V2 feature work.

### 0.2 Decisions that must not remain implicit

Before implementation, write short architecture decision records for:

- Field sample coordinates and image-to-mesh alignment.
- Procedural domain coordinates and frequency units.
- Tileable versus non-tileable generator behavior.
- Processing-stage order.
- Auto versus fixed-range normalization.
- Positive and negative relief semantics.
- Physical units and coordinate orientation.
- Reproducibility guarantees and tolerance.
- Project schema and migration policy.
- Generator algorithm versioning.
- Resource limits and failure behavior.
- ComfyUI scope and security boundary.

### 0.3 Recommended sampling convention

Use one explicit convention throughout V2:

- A field with shape `(rows, columns)` represents values at mesh vertices.
- Columns map left-to-right across the physical width.
- Rows map top-to-bottom across the physical depth, retaining the existing
  ClayField orientation documented in the README.
- Vertex coordinates use `i / (columns - 1)` and `j / (rows - 1)` for the
  non-tileable normalized domain.
- Imported images are resampled to this vertex lattice before mesh generation.
- A tileable generator explicitly samples a periodic domain and duplicates the
  seam at the final vertex when required.
- Preview and export use the same convention at different resolutions.

This decision prevents half-pixel shifts, generator/image misalignment, and
seams that appear only after export.

### 0.4 Recommended frequency convention

Procedural frequency must be expressed in domain terms, not unexplained pixel
magic:

- `1.0` means one complete cycle across the normalized generator domain.
- Separate X and Y frequency may be supported where useful.
- A physical-frequency option, if later added, converts from millimeters to
  normalized domain units before generation.
- Noise octave frequency uses `frequency *= lacunarity`.
- The UI must show enough context that a frequency value is meaningful at both
  512 and 1024 samples.

The current pixel-oriented noise scale can be preserved internally only behind
an explicitly versioned compatibility path.

### 0.5 Recommended field-stage order

Use this order as the V2 semantic contract:

```text
Source generation or import
→ source resampling
→ source composition
→ levels / gamma / contrast / curves
→ blur / sharpen / threshold
→ range policy
→ height mapping curve and clamp
→ edge falloff
→ physical mapping
→ solid mesh generation
```

Edge falloff is after the range and height mapping stages so the border can be
guaranteed to reach the declared low surface value. Fixed-range behavior must be
defined separately from auto-normalization; neither may be hidden inside a
generic clamp operation.

Existing V1 projects must retain their old stage semantics through a migration
compatibility mode if changing the order would alter their output.

### 0.6 Positive and negative relief contract

Preserve the current mesh convention unless a deliberate V2 breaking decision
is made:

- The physical height field is measured relative to the top of the base.
- Positive relief has surface values at or above `0 mm`.
- Negative relief has surface values at or below `0 mm`.
- The base extends downward to `-base_thickness_mm`.
- A positive relief with a 5 mm maximum and a 3 mm base has an 8 mm total solid
  height, without adding 3 mm to the surface array.
- A negative relief is invalid when its deepest recess reaches or passes the
  bottom of the base.

This avoids the common mistake of adding base thickness to the physical field
and accidentally producing an 11 mm object for the 3 mm base / 5 mm relief
example.

### 0.7 Reproducibility policy

Decide and document three levels of reproducibility:

**Exact regeneration**

The same project on the same supported software stack regenerates the same field
within a strict numerical tolerance.

**Cross-platform numerical regeneration**

The same project on supported platforms produces the same field within a looser
documented tolerance and the same physical extrema and mesh dimensions.

**Imported-result reproducibility**

An externally generated image is preserved by content hash and embedded data,
but may not be regenerated without the external tool.

Every procedural generator must store an algorithm identifier and version. A
future algorithm change must not silently reinterpret an old project.

### 0.8 Physical and fabrication decisions

Before adding printability warnings, define:

- Minimum supported and maximum supported physical dimensions.
- Whether feature-width warnings are based on raster samples, local slopes, or
  both.
- The default assumed printable feature size.
- Whether warnings are generic or material/printer profile based.
- Whether ceramic-specific rules are V2 scope or later.
- Whether slope is measured from the physical surface gradient or mesh triangle
  normals.
- Which metrics block export and which are advisory.

V2 should use generic, conservative advisory warnings. It should not claim that
a feature is printable for a particular printer or ceramic process without a
selected material/process profile.

### 0.9 Scope boundary before implementation

The V2 MVP should be locked to:

- Three native generators: noise, waves, and Mandelbrot.
- One secondary field.
- One mask.
- Explicit deterministic processing.
- Existing regular-grid solid meshes.
- Existing STL/3MF/heightmap formats.
- Procedural project persistence and V1 migration.

The following must remain post-MVP unless a measured blocker appears:

- General node editor.
- Multiple arbitrary field layers.
- Julia, Voronoi, reaction-diffusion, and erosion generators.
- Adaptive topology or mesh decimation.
- Ceramic firing compensation.
- Remote/cloud generation.
- Required ComfyUI installation.

### 0.10 Definition of Ready gate

V2 implementation is ready to begin only when:

- The baseline archive and current test result are recorded.
- Sampling, coordinate, frequency, stage-order, and relief semantics are
  written down.
- The source descriptor and pipeline snapshot shape are agreed.
- The project schema migration strategy is agreed.
- The three generator parameter sets are bounded and specified.
- The normalization and physical mapping behavior has example calculations.
- Resource limits are defined for preview, export, and Mandelbrot iterations.
- The MVP scope is frozen.
- A deterministic 100 x 100 mm acceptance specimen is specified.
- The first implementation slice has unit-test acceptance criteria.

No UI redesign or ComfyUI integration should begin before this gate passes.

### 0.11 Required technical spikes

Before building the full UI, implement or prototype these headless slices in a
temporary test module or small development script:

1. Generate a 32 x 32 noise field from a parameter snapshot.
2. Generate the same source at 512 x 512 and verify its domain semantics.
3. Map the field to a 100 x 100 mm, 5 mm relief.
4. Generate a closed solid with a 3 mm base.
5. Verify dimensions, volume, finite coordinates, and watertightness.
6. Serialize the source and mapping snapshot, reload it, and regenerate.
7. Compare preview and export extrema and a documented set of field samples.
8. Run the same smoke slice through an image source and a procedural source.
9. Exercise cancellation and stale-result rejection on a deliberately delayed
   generator.
10. Measure peak memory at the intended preview and export limits.

These spikes expose architectural problems before Qt panels, undo/redo, and
project migration make them expensive to fix.

### 0.12 Dependency, security, and provenance policy

Before adding external integrations, define:

- Supported Python, NumPy, OpenCV, SciPy, Qt, and Trimesh version ranges.
- Which numerical differences are accepted between dependency versions.
- Whether generator algorithms use only NumPy or introduce another dependency.
- How optional ComfyUI communication is disabled by default.
- Whether ComfyUI endpoints may be remote or only local-loopback.
- Request timeouts, response-size limits, and cancellation behavior.
- Treatment of imported workflows, model names, and generated assets as
  untrusted metadata.
- What provenance is retained without embedding copyrighted model files.

The core build must remain installable without network access, ComfyUI, a model,
or a GPU-capable desktop.

### 0.13 Acceptance users and workflows

Define acceptance around three users rather than only around modules:

**Image relief user**

Loads an image, adjusts it, maps it to physical height, and exports as before.

**Procedural designer**

Chooses a generator, changes seed and parameters, combines a field with a mask,
and exports a reproducible relief without importing an image.

**Fabrication operator**

Inspects dimensions, wall thickness, feature warnings, cross-sections, and
validation results before sending STL or 3MF to a slicer.

For each workflow, specify the shortest successful path, the expected visible
state during background processing, the recoverable failure states, and the
minimum information shown before export.

### 0.14 Failure behavior to design first

The V2 design must specify what happens when:

- A generator produces a constant field.
- A field contains NaN or infinity.
- Fixed-range parameters have equal minimum and maximum.
- A requested resolution exceeds the memory budget.
- Mandelbrot iterations exceed the workload budget.
- A source and mask have incompatible aspect ratios.
- A project uses an unknown generator version.
- A ComfyUI server is unavailable or returns a malformed image.
- A worker is cancelled after producing an intermediate stage.
- A stale result arrives after the user changes source parameters.
- A negative relief exceeds the base thickness.
- A mesh validates geometrically but has unacceptable fabrication warnings.

Errors must be actionable, preserve the previous valid result where possible,
and never replace a current field with a stale or partial result.

---

## 1. V2 Product Definition

### 1.1 Product goal

ClayField V2 will let a user create, inspect, modify, validate, and export
printable reliefs from any of these sources:

- An imported image or height map.
- A deterministic multiscale noise field.
- A Mandelbrot-derived mathematical field.
- A wave-interference field.
- A deterministic combination of those sources.
- An optional ComfyUI-generated image, texture, or mask.

The final result must be a reproducible normalized height field mapped to
explicit physical dimensions and converted to a validated closed solid.

### 1.2 V2 success statement

A user can create a 100 x 100 mm, 3 mm base, 5 mm relief fractal panel by
choosing a generator, setting a seed and parameters, previewing the result,
exporting a validated STL or 3MF, reopening the project, and reproducing the
same surface without requiring a neural network, a GPU, ComfyUI, or the
original preview resolution.

### 1.3 V1 foundation to preserve

V2 must retain and build on these working capabilities:

- Image loading and grayscale conversion.
- Non-destructive crop and resize.
- Levels, curves, brightness, contrast, blur, sharpen, and threshold.
- CPU-authoritative heightfield generation.
- GPU preview with CPU fallback.
- Background processing and stale-result protection.
- Positive and negative relief modes.
- Closed solid mesh generation.
- STL, 3MF, and 8/16-bit PNG/TIFF export.
- Mesh validation, dimension checks, and minimum-wall feedback.
- Undo/redo, presets, autosave/recovery, and project persistence.
- Cross-section inspection and export preview.

V2 is a product expansion, not permission to replace stable code without a
measured reason.

---

## 2. Product Principles

### 2.1 Deterministic by default

The same source type, parameters, seed, processing settings, resolution, and
software algorithm version must produce the same field within documented
floating-point tolerances.

### 2.2 Float fields are authoritative

The internal representations are:

```text
normalized_heightfield: float32 array, values normally in 0..1
physical_heightfield:   float32 array, values in millimeters
```

16-bit PNG/TIFF is an interchange and export format. It is not the authoritative
processing representation.

### 2.3 Physical meaning is explicit

The application must distinguish:

- Normalized intensity.
- Relative relief height.
- Absolute surface height.
- Base thickness.
- Total solid height.
- Exported coordinate orientation.

No UI label or project field should make these concepts ambiguous.

### 2.4 Preview is not export

Preview resolution and export resolution are independent. Procedural sources are
regenerated at export resolution from their stored parameters and seed rather
than upscaled from a preview.

### 2.5 No silent destructive changes

Normalization, clipping, smoothing, resampling, and generative replacement must
be visible operations with explicit settings. A model-generated image must never
silently replace a mathematical source.

### 2.6 Simple staged workflow, not a general node editor

V2 should expose a clear staged pipeline rather than arbitrary graph wiring:

```text
Source -> Compose -> Process -> Map -> Fabricate -> Validate -> Export
```

The implementation may use composable Python stages internally, but users do
not need to manage a complicated node graph.

### 2.7 Fabrication before decoration

Every feature is evaluated against physical dimensions, printability, memory
use, and export correctness. Visual novelty is not sufficient for inclusion.

---

## 3. Target V2 Workflow

```text
Source
  |-- Image / height map
  |-- Multiscale noise
  |-- Mandelbrot field
  |-- Wave interference
  `-- Optional ComfyUI result
          |
          v
Normalized float32 source field
          |
          v
Composition
  |-- Add / subtract
  |-- Multiply / mask
  |-- Minimum / maximum
  |-- Linear blend
  `-- Displacement
          |
          v
Deterministic image processing
  |-- Crop / resize
  |-- Levels / gamma
  |-- Contrast / curves
  |-- Blur / sharpen
  `-- Optional threshold
          |
          v
Height shaping
  |-- Auto or fixed-range normalization
  |-- Clamp
  |-- Edge falloff
  |-- Height inversion
  `-- Surface smoothing
          |
          v
Physical mapping
  `-- H = Hmin + I * (Hmax - Hmin)
          |
          v
Solid geometry
  |-- Top surface
  |-- Base
  |-- Side walls
  `-- Positive or negative relief
          |
          v
Fabrication analysis
  |-- Dimensions and scale
  |-- Watertightness
  |-- Volume and normals
  |-- Minimum wall
  |-- Minimum feature width
  `-- Slope and detail warnings
          |
          v
STL / 3MF / PNG / TIFF
```

The pipeline must have a single authoritative normalized field before physical
mapping and a single authoritative physical field before mesh construction.

---

## 4. Target Architecture

### 4.1 Proposed modules

The current modules remain valid. V2 adds focused modules rather than putting
all procedural behavior into `terrain/heightfield.py`.

```text
src/clayfield/
  field/
    __init__.py
    model.py              # field metadata, source descriptors, contracts
    generators.py         # deterministic procedural sources
    composition.py        # blend, mask, displacement operations
    processing.py         # field-level deterministic operations
    provenance.py         # hashes, algorithm versions, source metadata
  terrain/
    heightfield.py        # physical mapping and existing terrain modifiers
    fabrication.py        # printability metrics and warnings
  geometry/
    mesh_generator.py     # existing solid mesh path
    validation.py         # existing validation plus V2 checks
  integrations/
    comfyui.py            # optional API/file integration, no core dependency
  app/
    project_state.py      # source descriptors and V2 state
    project_io.py         # version 4+ migration and persistence
  ui/
    source_panel.py       # image and procedural source selection
    compose_panel.py      # explicit field composition
    fabrication_panel.py  # physical and printability controls
```

The exact module split may change during implementation, but the boundaries are
important:

- Generators produce normalized arrays.
- Composition combines normalized arrays.
- Processing transforms normalized arrays.
- Terrain mapping converts normalized arrays to millimeters.
- Geometry converts physical arrays to closed solids.
- Export never invents or alters terrain semantics.

### 4.2 Field contract

Every field-producing operation must define:

- Shape as `(rows, columns)`.
- `float32` dtype for published fields.
- Finite values only.
- Coordinate convention.
- Normalization contract.
- Seed behavior, if applicable.
- Cancellation behavior for worker execution.
- Whether resolution changes regenerate or resample data.

Suggested validation helper:

```python
validate_normalized_field(field, *, allow_out_of_range=False)
```

It should reject non-2D, empty, non-finite, unsupported dtype, and invalid
resolution data before the field reaches geometry generation.

### 4.3 Source descriptors

Replace the implicit assumption that every project has an image with an
explicit source descriptor.

Initial source types:

```text
image
heightmap
fractal_noise
mandelbrot
wave_interference
comfyui_image
```

Each descriptor contains:

- Type identifier.
- Schema version.
- Parameters.
- Seed, when applicable.
- Native or requested resolution.
- Optional embedded data or source reference.
- Algorithm version.
- Content hash where applicable.

### 4.4 Pipeline snapshot

The pipeline must be serializable independently of UI widgets. A pure snapshot
should be sufficient to regenerate a field and export it in a worker.

The snapshot contains:

- Source descriptor.
- Composition operations.
- Image/field processing settings.
- Mapping settings.
- Fabrication settings.
- Preview resolution.
- Export resolution.
- Algorithm compatibility version.

The UI state may contain caches and transient preview data, but those must not be
required to regenerate the project.

---

## 5. Numerical and Physical Contracts

### 5.1 Normalized field

The standard field contract is:

```text
I(x, y) in [0, 1]
```

Intermediate operations may temporarily exceed that range only when the stage
explicitly declares it. The next bounded stage must apply a named policy:

- Clip.
- Auto-normalize.
- Fixed-range normalize.
- Preserve signed range.

No generic `np.clip` should hide a range decision.

### 5.2 Physical mapping

For positive relief:

```text
surface_height = minimum_height + I * (maximum_height - minimum_height)
```

For a panel with a 3 mm base and 5 mm relief:

```text
base_bottom = 0 mm
base_top = 3 mm
surface_height = 3 mm + I * 5 mm
total_height = 8 mm
```

The existing internal coordinate convention may remain Y-up until export
orientation converts it for slicers.

### 5.3 Normalization modes

V2 must support at least:

**Auto normalization**

Maps the current minimum and maximum to `0..1`. This is useful for exploring a
field's full visual range.

**Fixed-range normalization**

Uses a declared source range and preserves amplitude changes. This is required
when a parameter should have a predictable physical effect.

The UI must show which mode is active and the actual pre- and post-normalization
ranges.

### 5.4 Resolution rules

- Preview and export sizes are independent.
- Procedural sources regenerate at target resolution.
- Imported images resample using the declared interpolation policy.
- Downsampling uses area filtering where appropriate.
- Export resolution is bounded by memory estimates.
- The project records resolution-independent parameters, not only cached arrays.

---

## 6. Procedural Generators

### 6.1 Multiscale noise, V2 MVP

Implement deterministic fBm-style noise first.

Parameters:

- `seed`.
- `base_frequency`.
- `octaves`, initially 1 through 8.
- `persistence` or gain.
- `lacunarity`, default 2.0.
- `amplitude`.
- `normalization`.
- Optional `ridged` mode after the baseline implementation.

Requirements:

- Same seed and parameters produce the same output.
- Output is independent of UI state.
- Output can be generated at arbitrary supported resolution.
- Noise is continuous enough for relief use.
- Frequency semantics are documented in physical and sample terms.
- Tests cover seed stability, parameter changes, shape, dtype, and bounds.

The current noise implementation can be extracted and improved rather than
discarded. Add lacunarity and a reusable field generator before adding more
noise styles.

### 6.2 Wave interference, V2 MVP

Implement planar and radial modes.

Parameters:

- Wave count.
- Frequency per wave.
- Direction or center.
- Amplitude per wave.
- Phase.
- Radial versus planar mode.
- Normalization mode.

Requirements:

- Symmetry cases have explicit tests.
- Phase changes produce predictable shifts.
- Radial center is expressed in normalized coordinates.
- Frequencies are documented relative to the field domain.

### 6.3 Mandelbrot-derived field, V2 MVP

Use smooth escape-time coloring rather than only integer iteration counts.

Parameters:

- Center real and imaginary coordinates.
- Zoom.
- Iteration count.
- Escape radius.
- Exponent, initially 2.
- Interior value policy.
- Contrast or curve.
- Inversion.

Requirements:

- Deterministic output.
- Bounded runtime for all UI settings.
- Explicit handling of points that do not escape.
- Smooth output suitable for blur and mesh generation.
- High-frequency detail warnings for export.

### 6.4 Deferred generators

Do not block the V2 release on:

- Julia sets.
- Voronoi and cellular fields.
- Reaction-diffusion.
- Domain-warped noise.
- Simulation-based erosion.
- GPU-only procedural generation.

The source descriptor and generator registry should allow these later without
requiring a project format rewrite.

---

## 7. Field Composition and Processing

### 7.1 Composition operations

Implement a small explicit operation set:

- Add.
- Subtract.
- Multiply.
- Minimum.
- Maximum.
- Linear blend.
- Masked blend.
- Scalar displacement.

Every operation must declare its output range policy.

Example:

```text
combined = lerp(fractal_field, organic_texture, mask * blend_amount)
```

### 7.2 Masks

Initial masks can come from:

- Imported grayscale images.
- Generated radial masks.
- Edge falloff masks.
- Simple procedural fields.

Mask controls:

- Invert.
- Blur.
- Contrast.
- Strength.

Multiple arbitrary layers are not required for the first V2 milestone. One
primary field, one secondary field, and one mask are sufficient to prove the
architecture.

### 7.3 Processing stages

Reuse existing image processing where semantics match. Add field-level APIs so
procedural sources do not need to be converted through temporary image files.

Initial stages:

- Crop.
- Resize.
- Levels.
- Gamma.
- Brightness.
- Contrast.
- Curves.
- Blur.
- Sharpen.
- Threshold.
- Smoothing.
- Edge falloff.
- Inversion.
- Clamp.
- Normalization.

The processing pipeline must be cacheable by immutable stage keys. A source
parameter edit should invalidate source-dependent stages, while a base-thickness
edit must not regenerate the height field.

---

## 8. ComfyUI Integration Boundary

### 8.1 Role of ComfyUI

ComfyUI is an optional exploration and image-processing provider. It is not a
required runtime dependency and is not the authority for mathematical fields or
physical mapping.

Useful uses:

- Generate organic texture candidates.
- Generate masks.
- Explore image variations.
- Apply visual processing workflows.
- Produce multiple candidates for later selection.

### 8.2 Exactness rule

Do not allow a generative model to modify a mathematical height field when the
user expects the original surface to remain exact.

The UI must clearly distinguish:

- Mathematical source.
- Generated visual source.
- Deterministic processing.

### 8.3 Integration stages

**Stage A: file interchange**

- Import PNG/TIFF heightmaps and masks.
- Export current normalized field.
- Preserve source metadata and hashes.

**Stage B: workflow provenance**

- Store ComfyUI workflow JSON.
- Store model identifier if supplied.
- Store seed and output hash.
- Store input hash.
- Show provenance in the project information panel.

**Stage C: optional API**

- Connect to a configured local ComfyUI endpoint.
- Submit a workflow only on explicit user action.
- Poll progress without blocking the UI.
- Import the result as a new source or secondary field.
- Handle unavailable endpoint, timeout, cancellation, and malformed output.

The V2 release must be fully useful with ComfyUI absent.

For the core V2 desktop release, ComfyUI is intentionally an external authoring
tool rather than an in-app workflow interface. Users can generate or process a
heightmap or mask in ComfyUI, export it, and import it through ClayField's
secondary-field or mask controls. The local API adapter remains available as
post-V2 tooling and does not block the core V2 release.

### 8.4 CLI and process policy

The V2 core must not depend on a ComfyUI CLI, shell command, or running model
server. Native Python/NumPy generators, deterministic processing, physical
mapping, and mesh export remain the authoritative path.

The preferred optional integration is the local ComfyUI HTTP/WebSocket API:

```text
ClayField
  -> submit explicit workflow JSON
  -> receive progress and output image/mask
  -> import as an identified external source
  -> deterministic ClayField processing
  -> physical mapping and export
```

ClayField may later offer an explicit user-configured command to launch a local
ComfyUI server, but it must not silently install dependencies, download models,
launch arbitrary commands, or require a server for normal operation.

A future headless batch adapter may expose a command such as:

```text
clayfield --comfy-workflow workflow.json --input source.png --output result.png
```

That adapter is optional and must reuse the same provenance, timeout, output
validation, and import code as the desktop API integration. It is not a V2 core
build dependency and must not redefine mathematical fields.

---

## 9. Geometry and Fabrication

### 9.1 Solid generation

Retain the regular-grid mesh as the primary V2 geometry path.

Requirements:

- Exact requested physical width and depth.
- Explicit base thickness.
- Positive and negative relief support.
- Closed side walls.
- Consistent winding and normals.
- No duplicate or degenerate faces.
- Chunked generation for large fields.
- Cancellation checkpoints.

### 9.2 Printability analysis

Add a fabrication analysis stage with metrics and warnings for:

- Minimum wall thickness.
- Minimum ridge width.
- Minimum valley width.
- Maximum local slope.
- High-frequency detail concentration.
- Isolated peaks or pits.
- Negative-relief base clearance.
- Physical height range.
- Estimated mesh memory.

The first implementation may use conservative sampled estimates. It must label
sampled estimates as estimates and must not present them as guarantees.

### 9.3 Optional detail conditioning

Provide explicit tools for:

- Low-pass smoothing below a user-selected feature scale.
- Detail attenuation.
- Ridge preservation where practical.
- Border flattening.

Never apply these automatically during export without showing the operation and
recording it in the project.

### 9.4 Mesh density strategy

V2 should keep a regular grid as the authoritative geometry representation.

Adaptive subdivision or error-bounded decimation may be investigated after V2
MVP if memory or export time becomes a measured bottleneck. It must preserve:

- Physical dimensions.
- Surface error bounds.
- Watertightness.
- Relief extrema within the declared tolerance.

---

## 10. User Interface Plan

### 10.1 V2 panels

Reorganize the current workflow into these conceptual panels while preserving
familiar controls:

**Source**

- Image or procedural source selector.
- Source-specific controls.
- Seed and randomize action.
- Source resolution and preview.

**Compose**

- Primary and secondary field selection.
- Blend operation.
- Blend amount.
- Mask selection and controls.

**Process**

- Crop and resize.
- Levels and curves.
- Contrast, blur, sharpen, threshold.
- Smoothing and edge treatment.

**Height**

- Auto/fixed normalization.
- Minimum and maximum height.
- Gamma and height curve.
- Clamp, offset, scale, inversion.

**Fabricate**

- Width and depth.
- Base thickness.
- Positive/negative mode.
- Preview/export resolution.
- Printability metrics.

**Export**

- STL/3MF/heightmap selection.
- Preview and validation summary.
- Estimated memory and output dimensions.
- Export progress and cancellation.

### 10.2 Preview requirements

Add or retain these synchronized views:

- Source field.
- Processed normalized field.
- Physical heightmap.
- 3D terrain.
- Cross-section.
- Fabrication warning overlay.

The user must be able to inspect the 2D field independently of lighting and
perspective in the 3D viewport.

### 10.3 Presets

Add V2 presets for:

- 100 x 100 mm fractal panel.
- Mountain tile.
- Mandelbrot branching relief.
- Wave interference panel.
- Low-detail print-safe relief.

Presets store parameters and pipeline descriptors, not large cached arrays.

---

## 11. Project Format and Migration

### 11.1 Project format target

Use a new project schema version for V2. The current project format should remain
loadable through an explicit migration path.

The V2 metadata must support:

- Image-backed projects.
- Procedural-only projects.
- Mixed procedural and image sources.
- Composition operations.
- Processing pipeline.
- Physical fabrication settings.
- ComfyUI provenance.
- Algorithm compatibility version.
- Preview/export settings.

### 11.2 Migration policy

- Existing V1/V0.3 image projects open unchanged.
- Their image becomes an `image` source descriptor.
- Existing terrain noise settings become the equivalent V2 modifier settings.
- No old setting is silently discarded.
- Saving a migrated project writes the new schema only after successful load.
- Failed migration leaves the current project untouched.

### 11.3 Reproducibility metadata

Store:

- Product version.
- Project schema version.
- Generator algorithm version.
- Processing algorithm version.
- Source hashes.
- Seed values.
- Field shape and dtype contract.
- Physical units.

If exact regeneration cannot be guaranteed because an external generated image is
used, the project should say so explicitly and retain the imported result.

---

## 12. Performance and Resource Policy

### 12.1 CPU first

NumPy and existing OpenCV/SciPy paths are sufficient for the initial procedural
generators. Do not add GPU generation merely because the viewport uses OpenGL.

### 12.2 Background execution

Run these operations in workers:

- Procedural generation at large resolution.
- Field composition.
- Field processing.
- Heightfield mapping.
- Mesh generation.
- Validation.
- Export.
- Optional ComfyUI requests.

Every long stage needs:

- Cancellation checkpoints where practical.
- Stale-result protection.
- Progress reporting where useful.
- Error propagation to the UI.

### 12.3 Cache policy

Cache immutable stages using keys that include:

- Upstream source identity.
- Source parameters.
- Resolution.
- Processing parameters.
- Algorithm version.

Do not cache mutable UI objects or share arrays across threads without clear
ownership rules.

### 12.4 Safety limits

The application must protect users from accidental allocations by checking:

- Maximum pixel count.
- Maximum estimated field memory.
- Maximum mesh memory.
- Maximum export size.
- Maximum Mandelbrot iteration workload.
- Maximum ComfyUI response size.

Limits should be configurable only after conservative defaults are proven.

---

## 13. Testing Strategy

### 13.1 Unit tests

Add coverage for:

- Field validation.
- Generator determinism.
- Generator bounds and dtype.
- Seed changes.
- Resolution changes.
- Wave symmetry and phase.
- Mandelbrot interior handling.
- Composition operators.
- Mask behavior.
- Normalization modes.
- Physical mapping.
- Provenance and hashes.
- Project schema validation.
- Migration from 0.3 projects.

### 13.2 Property and invariant tests

Test invariants such as:

- Same input snapshot gives the same output.
- Field shape matches requested resolution.
- Output contains no NaN or infinity.
- Fixed-range mapping preserves declared amplitude.
- Physical dimensions match requested dimensions.
- Positive relief never creates a negative base wall.
- Negative relief respects base thickness warnings.
- Mesh validation rejects malformed geometry.

### 13.3 UI tests

Cover:

- Switching image/procedural source.
- Changing seed and regenerating.
- Undo/redo for generator controls.
- Source and field preview modes.
- Procedural project save/load.
- V1 project migration.
- Stale procedural results.
- Export after source changes.
- Printability warning display.

### 13.4 Integration tests

Add optional checks for:

- STL dimensions and manifoldness.
- 3MF validity.
- PrusaSlicer slicing.
- ComfyUI mock API behavior.
- Large procedural export.
- Cancellation during generation and export.

### 13.5 Golden fixtures

Create small deterministic fixtures for each generator. Store parameters and
expected statistics rather than unnecessarily large full-resolution arrays:

- Shape.
- Min/max.
- Mean.
- Selected sample values.
- Stable hash where platform tolerance permits.

---

## 14. Manageable V2 Build Batches

The detailed phases below are grouped into seven build batches. A batch is a
coherent unit of work that can be implemented, tested, reviewed, and paused
without leaving the application in an ambiguous state.

Do not start a later batch because a previous batch is inconvenient. The exit
gate is the dependency boundary.

### Batch 0: Baseline, Decisions, and Test Harness

Maps to: Phase 0 and the Pre-Build Definition Of Ready.

Purpose:

Establish a safe V2 starting point and remove ambiguity before production code
changes begin.

Build:

- Verify the archived V1 backup and preserve its checksum.
- Set up the supported Python/test environment.
- Run the complete V1 baseline suite.
- Preserve representative image, heightmap, STL, and 3MF fixtures.
- Record current dimensions, orientation, and slicer behavior.
- Decide branch/tag/worktree strategy.
- Write the field, sampling, coordinate, frequency, stage-order, and relief
  contracts.
- Define the project schema direction and algorithm version policy.
- Define memory, resolution, iteration, and cancellation limits.
- Build the first headless smoke-test harness.

Do not build:

- New generators.
- New UI panels.
- ComfyUI integration.
- Project schema changes.

Exit gate:

- V1 tests pass in a recorded environment.
- The backup is recoverable and independently identified.
- The headless smoke test can map a small field to a validated solid.
- The V2 scope and numerical contracts are approved.

### Batch 1: Deterministic Field Engine

Maps to: Phases 1 and 2.

Purpose:

Build the pure Python/NumPy core that creates normalized fields without Qt,
images, ComfyUI, or mesh-specific logic.

Build:

- Add field validation and immutable field metadata.
- Add source descriptors and a generator registry.
- Extract and improve current fractal noise.
- Add lacunarity and explicit frequency semantics.
- Implement wave interference.
- Implement smooth Mandelbrot coloring.
- Add source-specific parameter validation.
- Add deterministic algorithm identifiers and versions.
- Add seed, resolution, bounds, and shape tests.
- Add cancellation and workload-limit support.
- Add golden fixtures with expected statistics and sample values.

Do not build:

- Qt source controls.
- ComfyUI API calls.
- Field blending UI.
- New mesh topology.

Exit gate:

- Noise, waves, and Mandelbrot generate fields without an image.
- Identical snapshots reproduce identical fields within the documented
  tolerance.
- All fields are finite, bounded according to their declared contract, and
  valid at preview and export resolutions.
- The generator core can be tested entirely headlessly.

### Batch 2: Authoritative Pipeline and Fabrication Core

Maps to: Phases 3 and 4, plus the geometry changes required by those phases.

Purpose:

Turn independent sources into one deterministic normalized field, map it to
physical millimeters, and prove that it produces printable solids.

Build:

- Add primary/secondary field composition.
- Add blend modes, scalar amounts, and one mask.
- Add field-level crop, resize, levels, curves, blur, sharpen, and threshold
  operations.
- Add explicit output range policies.
- Add auto versus fixed-range normalization.
- Add height mapping, clamp, inversion, and edge falloff semantics.
- Preserve V1 behavior through compatibility handling where required.
- Add physical height and total-solid-height calculations.
- Add minimum wall, feature-width, slope, and high-frequency estimates.
- Add fabrication warning categories and blocking rules.
- Verify regular-grid mesh generation for procedural fields.
- Add deterministic 100 x 100 mm acceptance geometry.

Do not build:

- Final V2 UI layout.
- Multiple arbitrary field layers.
- Adaptive meshes.
- Material-specific print claims.

Exit gate:

- A procedural field can be blended with an image or mask.
- Fixed-range amplitude changes have predictable physical effects.
- The 100 x 100 mm / 3 mm base / 5 mm relief example has correct dimensions.
- STL and 3MF validation succeeds for all three generators.
- Fabrication warnings are computed from the authoritative field, not the GPU
  preview.

### Batch 3: V2 State, Persistence, and Worker Integration

Maps to: Phase 5, with required worker and cache integration from Phases 1-4.

Purpose:

Make the new field pipeline a durable application feature rather than a test
library.

Build:

- Add procedural source state to the project model.
- Add serializable pipeline snapshots.
- Add source, composition, processing, mapping, and fabrication persistence.
- Add procedural-only projects.
- Migrate existing 0.3 image projects transactionally.
- Persist algorithm versions, source hashes, seeds, and provenance.
- Add worker execution for generation, composition, mapping, and validation.
- Add stale-result protection for procedural changes.
- Add cancellation and progress propagation.
- Extend cache keys to include source parameters and algorithm versions.
- Add autosave/recovery support for procedural projects.

Do not build:

- Optional ComfyUI API support.
- Final panel redesign.
- New post-MVP generators.

Exit gate:

- A procedural project saves, closes, reopens, and reproduces its field.
- Existing V1 projects migrate without changing their intended behavior.
- A stale or cancelled worker cannot replace current project state.
- Large generation and export operations leave the UI responsive.

### Batch 4: User Workflow and Fabrication UI

Maps to: Phase 6.

Purpose:

Expose the proven field and fabrication pipeline through a clear workflow while
preserving the existing image-relief path.

Build:

- Add Source controls for image, noise, waves, and Mandelbrot.
- Add seed randomization and source presets.
- Add Compose controls for one secondary field and one mask.
- Reorganize processing controls without changing their semantics.
- Add Height controls for normalization and physical mapping.
- Add Fabricate controls for dimensions, base, relief mode, and resolution.
- Add source, normalized-field, physical-heightmap, and 3D preview modes.
- Add fabrication-warning overlays and summaries.
- Preserve cross-sections, export preview, undo/redo, presets, and recovery.
- Add UI tests for source switching, stale results, save/load, and export.

Do not build:

- A general node editor.
- Hidden automatic processing.
- ComfyUI as a required workflow step.

Exit gate:

- A procedural designer can complete the full workflow without an image.
- An existing image user can follow the old workflow.
- A fabrication operator can inspect all required warnings before export.
- All long operations remain responsive and cancellable.

### Batch 5: Optional ComfyUI and External Provenance

Maps to: Phase 7.

Purpose:

Add external visual exploration without making it part of the deterministic core.

Build:

- [x] Add API-format workflow and output provenance models.
- [x] Add optional local ComfyUI HTTP API client and output import validation.
- [x] Add submit, history polling, progress, cancellation, timeout, response
  limits, and malformed-output handling.
- [x] Add mock-server tests and offline behavior tests.
- [ ] Add heightmap and mask file interchange UI.
- [ ] Import external results as explicit secondary sources in the UI.
- [ ] Store imported workflow results through the project UI.
- Clearly label mathematical, imported, and model-generated sources.

Do not build:

- Mandatory ComfyUI installation.
- Comfy CLI as a required or primary integration path.
- Silent model modification of mathematical fields.
- Remote execution by default.
- Model-file bundling.

Exit gate:

- V2 is fully usable with ComfyUI absent.
- External results cannot silently replace mathematical sources.
- Imported results and their provenance survive project save/load.
- Failure of the external service leaves the last valid field intact.

### Batch 6: Production Hardening and V2 Release

Maps to: Phases 8, 9, and 10.

Purpose:

Prove the complete product under realistic workloads and produce a releasable
V2 artifact.

Build:

- Profile 512² and 1024² procedural generation and export.
- Verify memory guards and peak RSS behavior.
- Reduce unnecessary array copies.
- Complete cancellation and progress coverage.
- Run all unit, property, UI, export, GPU, stress, and migration tests.
- Run STL/3MF validation for every generator and representative composition.
- Run PrusaSlicer digital QA.
- Perform physical print validation when hardware is available.
- Test fresh installation, wheel, bundle, self-test, and GL self-test.
- Update README, user guide, development documentation, and changelog.
- Produce deterministic sample projects and acceptance artifacts.
- Version the product as `2.0.0` only after all release gates pass.

Do not build:

- New major features during release hardening.
- Unmeasured optimization systems.
- Scope additions disguised as release fixes.

Exit gate:

- All release gates in Section 17 pass.
- V1 migration and V2 regeneration are verified.
- Representative files are slicer-compatible and dimensionally correct.
- The release can be installed and tested from a clean environment.

### Batch dependency map

```text
Batch 0  Baseline and contracts
   |
   v
Batch 1  Deterministic field engine
   |
   v
Batch 2  Pipeline and fabrication core
   |
   v
Batch 3  Persistence and workers
   |
   v
Batch 4  User workflow UI
   |
   +----------------------+
   |                      |
   v                      v
Batch 5  Optional ComfyUI  Batch 6  Production hardening
                              ^
                              |
                       Batch 5 can run in parallel
                       after Batch 4 but must finish
                       before the final release gate.
```

Batch 5 is intentionally isolated. It should not delay the core procedural
product, and it should not be allowed to redefine the field or project model.

---

## 15. Active Detailed Build Board

This is the execution checklist for the current implementation. The batch
sections above describe the intent; this board identifies the smallest reviewable
tasks. Complete tasks in order within each batch unless a task is explicitly
marked independent.

### Batch 0: Baseline and Contracts

- [x] Confirm the V1 virtual environment and dependency imports.
- [x] Record the V1 test baseline.
- [x] Record the V1 backup path and SHA-256.
- [ ] Validate the 7-Zip archive contents with an available archive tool.
- [x] Document field dtype, bounds, coordinates, and physical relief semantics.
- [x] Add the headless field-to-mesh smoke path.
- [ ] Record a clean-machine restore procedure.

Batch gate: the baseline can be restored and the V2 contracts are testable
without opening the Qt application.

### Batch 1: Deterministic Field Engine

- [x] Add immutable normalized-field validation.
- [x] Add source metadata and algorithm versions.
- [x] Implement deterministic multiscale noise.
- [x] Implement tileable noise boundary rules.
- [x] Implement planar and radial waves.
- [x] Implement smooth Mandelbrot fields.
- [x] Add parameter validation and workload bounds.
- [x] Add generator golden/invariant tests.
- [x] Add deterministic procedural-to-mesh coverage.

Batch gate: all native sources generate finite reproducible fields without Qt,
ComfyUI, or image files.

### Batch 2: Pipeline and Fabrication Core

- [x] Define the fixed processing stage order.
- [x] Add field resize, levels, curves, blur, sharpen, and threshold stages.
- [x] Add clip and auto-normalize policies.
- [x] Add field composition primitives.
- [x] Add normalized-to-physical mapping.
- [x] Add mapping curves, clamp, scale, offset, inversion, and edge falloff.
- [x] Add minimum wall and sampled feature-width metrics.
- [x] Add slope and high-frequency heuristics.
- [x] Add blocking versus advisory warning categories.
- [x] Add physical pipeline output object.
- [x] Add procedural export task coverage.

Batch gate: a composed field maps to a dimensionally correct, validated solid
with conservative fabrication diagnostics.

### Batch 3: State, Persistence, and Workers

- [x] Add source descriptors and pipeline snapshots.
- [x] Add procedural-only project files.
- [x] Add schema version 4 migration from V1 projects.
- [x] Add content hashes and algorithm provenance.
- [x] Add procedural autosave and recovery.
- [x] Add stable resolution-aware pipeline cache keys.
- [x] Add worker-safe serialized pipeline evaluation.
- [x] Add cancellation and progress callbacks.
- [x] Add transactional malformed-project rejection.

Batch gate: procedural projects save, reopen, regenerate, recover, and reject
stale or invalid state without damaging the active project.

### Batch 4: User Workflow and Fabrication UI

- [x] Add image/procedural source selection.
- [x] Add noise, wave, and Mandelbrot controls.
- [x] Add background procedural preview generation.
- [x] Add procedural STL, 3MF, and heightmap regeneration at export resolution.
- [x] Separate preview-affecting keys from export-only resolution changes.
- [x] Add secondary-field enable/disable control.
- [x] Add secondary source selector and source controls.
- [x] Add blend operation and amount controls.
- [x] Add radial mask, invert, feather, and strength controls.
- [x] Persist composition and mask settings through projects and undo/redo.
- [x] Add fabrication metrics to the terrain panel.
- [x] Add warning and export-blocking presentation.
- [x] Add composition and fabrication controls to export preview.
- [ ] Consolidate the UI into Source, Compose, Process, Height, Fabricate, and
  Export sections without breaking existing image workflows.

Batch gate: image users, procedural users, and fabrication operators can each
complete the workflow and understand the field and fabrication warnings before
export.

### Batch 5: Optional ComfyUI Integration

- [x] Inspect the local ComfyUI API examples and endpoint contract.
- [x] Add API-format workflow descriptor and canonical hash.
- [x] Add local HTTP queueing and history polling.
- [x] Add output download and normalized image validation.
- [x] Add model, seed, prompt, workflow, and output provenance.
- [x] Add timeout, response-size, malformed-response, and offline handling.
- [x] Add mock ComfyUI server tests.
- [x] Add workflow file selection in the UI.
- [x] Add explicit ComfyUI submit/progress/cancel controls.
- [x] Import output as a secondary field without replacing mathematical sources.
- [x] Add mask import and heightmap file interchange controls.
- [x] Persist imported outputs and provenance in project files.
- [x] Add optional API endpoint settings.
- [ ] Add an optional batch CLI adapter only if real workflows require it.

Batch gate: ComfyUI improves exploration but remains optional, local, labeled,
provenance-preserving, and outside the authoritative mathematical path.

### Batch 6: Production Hardening and Release

- [ ] Profile 512² and 1024² procedural generation.
- [ ] Profile procedural mesh and export memory.
- [ ] Verify cancellation under large workloads.
- [ ] Run complete unit, UI, export, GPU, stress, and migration suites.
- [ ] Run STL/3MF slicer checks for all native generators.
- [ ] Run offline tests with no ComfyUI installation.
- [ ] Verify fresh wheel and bundle installation.
- [x] Verify packaged self-tests and OpenGL self-tests.
- [ ] Produce deterministic sample projects and export artifacts.
- [ ] Perform physical print validation when hardware is available.
- [ ] Update release notes and acceptance report.
- [~] Version/release the product as `2.0.0` after remaining external gates pass.

Batch gate: a clean installation can reproduce representative projects and
produce slicer-compatible, dimensionally correct output.

---

## 16. Phased Roadmap

Each phase has an implementation scope, a test gate, and a completion condition.

### Phase 0: V2 foundation and freeze

Tasks:

- [ ] Tag or archive the current 0.3.0 baseline.
- [ ] Confirm the current full test suite passes.
- [ ] Record current project schema and migration behavior.
- [ ] Record current STL/3MF dimension and slicing behavior.
- [ ] Create V2 feature flag or branch strategy.
- [ ] Define field contracts and algorithm-version policy.
- [ ] Add a V2 development checklist to the repository.

Exit criteria:

- The baseline can be restored independently of V2 work.
- Existing image projects remain loadable.
- The V2 contracts are reviewed before implementation begins.

### Phase 1: Field core and procedural source abstraction

Tasks:

- [ ] Add field validation and immutable field metadata.
- [ ] Add source descriptor types and registry.
- [ ] Extract current noise generation into a reusable generator.
- [ ] Add lacunarity and explicit normalization policy.
- [ ] Add deterministic fBm tests.
- [ ] Add procedural source worker execution.
- [ ] Add preview/export resolution separation for procedural sources.
- [ ] Keep image source behavior unchanged.

Exit criteria:

- A procedural noise field can be generated without an image.
- Same snapshot and seed reproduce the same field.
- Existing image-to-relief tests pass unchanged.

### Phase 2: Procedural generator MVP

Tasks:

- [ ] Implement wave-interference generator.
- [ ] Implement smooth Mandelbrot-derived generator.
- [ ] Add source-specific parameter validation.
- [ ] Add source previews and histogram/range reporting.
- [ ] Add source randomize-seed action.
- [ ] Add generator presets.
- [ ] Add cancellation and workload limits.

Exit criteria:

- Noise, waves, and Mandelbrot can each produce an STL/3MF without an image.
- Generator outputs are finite, bounded, and reproducible.
- Large or invalid parameter combinations fail clearly instead of freezing the UI.

### Phase 3: Pipeline composition and processing

Tasks:

- [ ] Add primary/secondary field composition.
- [ ] Add blend amount and blend modes.
- [ ] Add one mask input with invert, blur, contrast, and strength.
- [ ] Move shared processing operations behind field-level APIs.
- [ ] Add explicit range policies after each composition stage.
- [ ] Add stage-keyed caching.
- [ ] Add normalized-field and physical-field comparison views.

Exit criteria:

- A fractal can be blended with an imported image or mask.
- Processing changes do not regenerate unrelated stages.
- The final normalized field is inspectable and reproducible.

### Phase 4: Physical mapping and fabrication safety

Tasks:

- [ ] Add auto versus fixed-range normalization.
- [ ] Clarify minimum/maximum surface height labels.
- [ ] Add physical height and total solid height readouts.
- [ ] Add minimum feature-width estimate.
- [ ] Add slope estimate.
- [ ] Add high-frequency detail warning.
- [ ] Add print-safe smoothing/detail attenuation as explicit operations.
- [ ] Add fabrication presets.

Exit criteria:

- A 100 x 100 x 8 mm test panel reports correct dimensions.
- Changing amplitude under fixed-range mapping changes physical relief depth.
- Export preview reports fabrication warnings before export.

### Phase 5: Project schema V2 and migration

Tasks:

- [ ] Define the V2 project schema.
- [ ] Persist source descriptors.
- [ ] Persist composition and processing pipelines.
- [ ] Persist algorithm versions and hashes.
- [ ] Support procedural-only projects.
- [ ] Migrate 0.3 image projects transactionally.
- [ ] Add malformed and unsupported-schema tests.
- [ ] Ensure autosave/recovery supports procedural projects.

Exit criteria:

- A procedural project can be closed, reopened, and regenerated identically.
- A 0.3 project opens without manual conversion.
- Failed migration does not modify the active project.

### Phase 6: V2 interface consolidation

Tasks:

- [ ] Add Source panel.
- [ ] Add Compose panel.
- [ ] Reorganize Process controls without breaking shortcuts or behavior.
- [ ] Add Height and Fabricate summaries.
- [ ] Add source/field/physical preview modes.
- [ ] Add generator and fabrication presets.
- [ ] Add clear busy, stale, cancelled, and failed states.
- [ ] Add accessible labels and tooltips for physical units.

Exit criteria:

- A first-time user can complete the procedural panel workflow without editing
  project JSON or loading an image.
- Existing image users can still follow the current workflow.
- All long operations remain responsive.

### Phase 7: Optional ComfyUI integration

Tasks:

- [ ] Implement heightmap/mask file interchange.
- [ ] Add provenance metadata for imported ComfyUI results.
- [ ] Add optional local API configuration.
- [ ] Add submit, progress, cancellation, timeout, and error handling.
- [ ] Import results as explicit secondary sources.
- [ ] Add mock-server tests.
- [ ] Document that ComfyUI is optional.

Exit criteria:

- V2 builds and runs with no ComfyUI installation.
- A ComfyUI result cannot silently replace a mathematical source.
- Imported results remain identifiable and exportable.

### Phase 8: Geometry and production hardening

Tasks:

- [ ] Profile procedural generation and export at 512² and 1024².
- [ ] Reduce unnecessary array copies.
- [ ] Verify chunked mesh generation on procedural fields.
- [ ] Improve cancellation checkpoints.
- [ ] Verify memory guardrails.
- [ ] Run STL and 3MF validation across generator types.
- [ ] Run PrusaSlicer digital QA for representative fields.
- [ ] Produce at least one physical print when hardware is available.

Exit criteria:

- Representative fields export within documented resource limits.
- All formats are dimensionally correct and slicer-compatible.
- No known generator-specific watertightness failures remain.

### Phase 9: V2 release candidate

Tasks:

- [ ] Run full unit, UI, stress, GPU, export, and optional integration suites.
- [ ] Test fresh installation and migration from the archived baseline.
- [ ] Update README and user guide.
- [ ] Add V2 changelog entry.
- [ ] Update bundle and wheel build paths.
- [ ] Verify `--self-test` and `--gl-self-test`.
- [ ] Produce deterministic sample projects and export artifacts.
- [ ] Perform a clean-machine release rehearsal.

Exit criteria:

- All release gates pass.
- V2 sample projects reopen and reproduce expected fields.
- Release artifacts are locally installable and self-tested.

### Phase 10: V2.0.0 release

Tasks:

- [x] Update version to `2.0.0`.
- [ ] Document schema and migration support.
- [ ] Publish local release artifacts according to repository policy.
- [ ] Archive the final V2 acceptance report.
- [ ] Create a V2.1 backlog from measured user feedback.

---

## 17. Release Gates

V2 is not ready for release unless all of these are true:

### Functional

- Image sources still work.
- Procedural noise works without an image.
- Wave interference works without an image.
- Mandelbrot fields work without an image.
- Mathematical fields can be composed with images and masks.
- STL and 3MF exports are closed and dimensionally correct.
- PNG/TIFF heightmap export remains available.

### Determinism

- Seeded procedural fields reproduce from project parameters.
- Preview and export use the same mathematical source definition.
- Project reopen reproduces the final field within documented tolerance.
- External generated sources record provenance and are not misrepresented as
  mathematically reproducible.

### Fabrication

- Physical dimensions are explicit and verified.
- Base thickness and negative relief safety are checked.
- Mesh validation reports watertightness, volume, finite coordinates, and face
  quality.
- Feature and slope warnings are visible before export.

### Reliability

- Long operations run off the UI thread.
- Cancellation works at practical checkpoints.
- Stale results cannot overwrite current project state.
- Autosave and recovery handle procedural projects.
- Malformed projects fail transactionally.

### Compatibility

- Existing 0.3 projects migrate successfully.
- GPU preview is optional and CPU output remains authoritative.
- ComfyUI is optional.
- Fresh installation and bundled self-tests pass.

---

## 18. Explicit Non-Goals For V2

Do not make these release blockers:

- A general-purpose visual node editor.
- A required neural network or generative model.
- GPU-only procedural generation.
- Sculpting brushes.
- Full CAD-style Boolean modeling.
- Automatic topology optimization.
- Ceramic firing shrinkage compensation.
- Mold-release and draft analysis.
- Multi-tile production management.
- Cloud rendering or remote project storage.
- Mandatory ComfyUI installation.

These may be evaluated after V2 based on real usage and measured bottlenecks.

---

## 19. Immediate Implementation Sequence

When implementation begins, use this order:

1. Complete the Pre-Build Definition Of Ready and technical spikes.
2. Add field contracts and tests without changing the UI.
3. Extract current fractal noise into a standalone deterministic generator.
4. Add procedural-only source state and worker execution.
5. Add procedural source persistence and reopen tests.
6. Add waves and Mandelbrot generators.
7. Add fixed-range mapping.
8. Add composition and masks.
9. Add fabrication metrics and warnings.
10. Consolidate the UI around Source, Process, Height, Fabricate, and Export.
11. Add optional ComfyUI file/API integration.
12. Harden performance, migration, packaging, and release checks.

Do not start with ComfyUI integration or a visual node editor. The core V2 value
is a reproducible mathematical field that can be printed correctly without
external services.

---

## 20. V2 First Demonstration

The first end-to-end V2 demonstration should be reproducible from a clean
installation:

```text
Source:            Multiscale noise
Seed:              42
Octaves:           6
Persistence:       0.55
Lacunarity:        2.0
Base frequency:    2.0
Normalization:     Fixed range
Panel:             100 x 100 mm
Base:              3 mm
Relief:            5 mm
Preview:           512 x 512
Export:            1024 x 1024
Output:            STL and 3MF
```

The demonstration must show:

- The 2D normalized field.
- The physical height range.
- The 3D surface.
- The fabrication warnings.
- The export validation report.
- A reopened project reproducing the same field.

This is the acceptance specimen for the procedural V2 pipeline.

---

## 21. V2 Gap Register and Release Blockers

The core V2 workflow is working, but the following gaps must be tracked
explicitly. These are not optional feature ideas; they are the remaining risks
identified by reviewing the current implementation against the batch gates.

### 21.1 P0: Unify image and procedural composition

Current state:

- Procedural primary fields use the V2 composition pipeline.
- Image-primary projects still use the older image-specific heightfield path.
- Secondary and mask controls can be displayed for an image project, but the
  image-primary path does not yet evaluate them through the same V2 composition
  stages.

Required tasks:

- [x] Convert an image source into a normalized V2 primary field.
- [x] Route image-primary and procedural-primary projects through the same
  secondary-field and mask composition code.
- [ ] Preserve V1 image projects through an explicit compatibility mode where
  the old stage order must remain unchanged.
- [x] Add image-primary plus secondary-field tests.
- [ ] Add image-primary plus mask tests.
- [ ] Add image-primary plus ComfyUI-result tests.
- [ ] Show the active compatibility or V2 pipeline mode in project metadata.

Release gate:

An image user and a procedural user can apply the same composition operations
and receive the same normalized-field, physical-mapping, fabrication-analysis,
and export semantics.

### 21.2 P0: Protect against stale external results

Current risk:

A ComfyUI request can finish after the user opens a new project, changes the
source, or closes the current operation. Without an external-request generation
token, its result could be applied to the wrong project.

Required tasks:

- [x] Assign a request generation token to every ComfyUI operation.
- [ ] Capture the project revision and source descriptor hash when submitting.
- [x] Cancel the active request when opening or creating a project.
- [x] Cancel the active request when changing source or composition state.
- [x] Reject results whose project revision, source hash, or request token is no
  longer current.
- [ ] Distinguish cancellation from an execution failure in the UI.
- [ ] Add stale-result tests covering new project, source change, and close.

Release gate:

No external result can mutate a project other than the project that submitted
the request.

### 21.3 P0: Complete external provenance and exact-artifact policy

Current risk:

The ComfyUI source descriptor stores a workflow hash and output metadata, but
not the complete API-format workflow JSON. Embedded secondary and mask fields
are stored as 16-bit PNG representations, which may not preserve the exact
original output bytes or the original float data.

Required tasks:

- [x] Store the complete API-format workflow JSON in project provenance.
- [ ] Store the ComfyUI integration version.
- [x] Store the original returned output bytes when available.
- [x] Store the normalized working field separately from the display/export
  representation.
- [ ] Record the quantization policy for embedded 16-bit field files.
- [ ] Decide whether original bytes or float32 data is the canonical external
  artifact.
- [ ] Verify project reopen preserves the selected canonical artifact.
- [ ] Add malformed, truncated, and mismatched-provenance tests.

Release gate:

The application never claims exact regeneration when it only has a quantized or
external result, and the project contains enough provenance to inspect what was
actually imported.

### 21.4 P1: Complete ComfyUI workflow execution support

Required tasks:

- [ ] Add local ComfyUI `/upload/image` support for workflows containing
  `LoadImage` nodes.
- [ ] Add explicit source-image and mask upload mapping.
- [ ] Validate that uploaded files remain local and within the intended input
  boundary.
- [ ] Support multiple output nodes and multiple candidates.
- [ ] Let the user choose the output node, output index, and source role.
- [ ] Distinguish field, mask, preview, and candidate outputs.
- [ ] Add a local endpoint connection test.
- [ ] Restrict the default endpoint to loopback addresses.
- [ ] Require an explicit opt-in before allowing remote endpoints.
- [ ] Add an API response-size and output-count limit.
- [ ] Add optional real-server integration coverage when
  `CLAYFIELD_COMFYUI_URL` is configured.

Release gate:

ComfyUI workflows can use a selected local image or mask, and users never have
to guess which of several workflow outputs was imported.

### 21.5 P1: Make cancellation granular

Required tasks:

- [ ] Add cancellation checkpoints between Mandelbrot iteration blocks.
- [ ] Add cancellation checkpoints between procedural noise octaves.
- [ ] Add cancellation checkpoints between processing stages.
- [ ] Add cancellation checkpoints during fabrication analysis.
- [ ] Add cancellation checkpoints during external field resampling.
- [ ] Verify cancelled workers do not publish partial fields.
- [ ] Verify cancellation preserves existing export destinations.

Release gate:

Cancellation visibly completes within a bounded practical interval for supported
preview and export workloads.

### 21.6 P1: Version the complete pipeline

Current state:

Source generators have algorithm identifiers, but all stages that affect output
need explicit compatibility metadata.

Required tasks:

- [ ] Add source algorithm version.
- [ ] Add processing algorithm version.
- [ ] Add mapping algorithm version.
- [ ] Add fabrication-analysis version.
- [ ] Add external-import conversion version.
- [ ] Include dependency/runtime compatibility information where numerical
  variation matters.
- [ ] Reject or migrate projects whose algorithm versions are unsupported.
- [ ] Add cross-version golden fixtures.

Release gate:

An old project cannot silently change its generated field because an internal
algorithm or dependency changed.

### 21.7 P1: Final-resolution fabrication analysis

Current risk:

The current preview analysis is useful, but the final export field can have a
different resolution and therefore different sampling, slope, and detail
metrics.

Required tasks:

- [x] Regenerate or evaluate the final export-resolution field before export
  confirmation.
- [x] Calculate final-resolution wall thickness.
- [x] Calculate final-resolution resolved feature width.
- [x] Calculate final-resolution slope and high-frequency warnings.
- [x] Show preview metrics and export metrics separately when they differ.
- [ ] Block export only for explicitly blocking conditions.
- [ ] Keep generic heuristics clearly labeled as advisory.

Release gate:

The warnings shown before export describe the actual field that will be
exported, not only the lower-resolution preview.

### 21.8 P1: Fabrication profiles and calibration

Current metrics are generic raster and gradient heuristics. They do not claim
to model a particular printer, nozzle, material, ceramic body, or firing cycle.

Required tasks:

- [x] Define a generic default profile.
- [ ] Define optional printer/material profile schema.
- [ ] Store the selected profile in the project.
- [ ] Separate advisory warnings from export blockers.
- [x] Add a minimum-feature calibration fixture.
- [x] Add a slope calibration fixture.
- [x] Add a wall-thickness calibration fixture.
- [ ] Print and inspect representative calibration artifacts when hardware is
  available.
- [ ] Keep documentation explicit about the limits of generic warnings.

Release gate:

Fabrication diagnostics are measurable, labeled, and not presented as a
guarantee for an unspecified process.

### 21.9 P1: External field immutability and atomic publication

Required tasks:

- [x] Copy imported secondary and mask fields at the import boundary.
- [x] Validate them before publishing to project state.
- [x] Mark published arrays read-only.
- [x] Replace fields atomically after a successful import.
- [ ] Preserve the previous valid field if import or processing fails.
- [ ] Add worker tests for concurrent read and replacement boundaries.

Release gate:

Workers cannot observe partially imported or accidentally mutated external
arrays.

### 21.10 P1: Source and provenance UI

Required tasks:

- [ ] Show the primary source type and name.
- [ ] Show secondary and mask source types.
- [ ] Distinguish mathematical, imported, and model-generated sources.
- [ ] Show embedded versus externally reproducible status.
- [ ] Show workflow hash, output hash, and prompt ID for ComfyUI results.
- [ ] Warn before source switches that discard or replace data.
- [ ] Make image/procedural compatibility mode visible.

Release gate:

Users can understand exactly what field data is being composed and whether it
can be regenerated without an external service.

### 21.11 P2: Operational and release gaps

Required tasks:

- [ ] Validate `clayfield-v1.7z` contents with a 7-Zip-compatible tool.
- [ ] Record a clean-machine restore procedure.
- [ ] Add an optional live ComfyUI integration test.
- [ ] Establish the V2 development and release version sequence.
- [ ] Define project schema versus application version policy.
- [ ] Verify fresh wheel installation.
- [ ] Verify fresh bundle installation.
- [ ] Run packaged self-tests and OpenGL self-tests.
- [ ] Produce native, composed, imported, and ComfyUI-derived sample projects.
- [ ] Run slicer QA for all representative output classes.
- [ ] Perform physical print validation when hardware is available.

Release gate:

V2 can be restored, installed, tested, migrated, regenerated, sliced, and
documented from a clean environment.

---

## 22. Updated Master Build List

The following is the current authoritative order of work. Completed batches are
shown for context; unchecked work is the remaining V2 build.

### Batch 0: Baseline and Contracts

Status: mostly complete.

Remaining: archive-content validation and clean restore procedure.

### Batch 1: Deterministic Field Engine

Status: complete.

Noise, waves, Mandelbrot, normalized-field contracts, reproducibility tests,
tileable boundaries, and headless source generation are implemented.

### Batch 2: Pipeline and Fabrication Core

Status: core complete.

Composition, masks, processing, physical mapping, fabrication metrics, and
procedural export tasks are implemented. Final-resolution analysis and profile
calibration remain.

### Batch 3: State, Persistence, and Workers

Status: complete at the current schema boundary.

Procedural projects, migration, recovery, worker evaluation, cache keys,
external field embedding, and cancellation callbacks are implemented. Granular
cancellation and full algorithm compatibility versioning remain.

### Batch 4: User Workflow and Fabrication UI

Status: mostly complete.

Source controls, procedural preview, composition, masks, direct heightmap/mask
import, fabrication metrics, export preview, and procedural exports are
implemented.

Remaining: unified image/procedural composition, final-resolution warning
analysis, source/provenance UI, source-switch safety, and panel consolidation.

### Batch 5: Optional ComfyUI Integration

Status: core and first UI integration complete.

Workflow selection, local API submission, history polling, output import,
provenance, secondary-field composition, persistence, and direct file
interchange are implemented.

Remaining: stale-request tokens, complete workflow JSON persistence, original
artifact policy, input upload, output selection, endpoint restrictions, live
server testing, and optional CLI adapter evaluation.

### Batch 6: Production Hardening and Release

Status: not started.

Remaining: performance profiling, memory/cancellation stress, migration QA,
slicer QA, live ComfyUI QA, physical print calibration, packaging, versioning,
documentation, and the V2 release candidate.

### V2 release blockers

V2 should not be called release-ready until these are complete:

- Image-primary and procedural-primary composition share one authoritative field
  pipeline.
- Stale ComfyUI results cannot mutate a different project.
- External provenance and artifact preservation policy is complete.
- Final export-resolution fabrication analysis is visible before export.
- Pipeline algorithm versions are persisted and migration-aware.
- External fields are immutable and atomically published.
- Representative native, composed, imported, and ComfyUI-derived projects pass
  clean-machine, slicer, and migration checks.

---

## 23. Additional Product Quality Plan

These are the final quality improvements after the core field, pattern,
composition, persistence, fabrication, and export systems are working.

### 23.1 Source Editor Parity

The primary and secondary source editors should share the same source-editor
contract:

- [ ] Source type selection.
- [ ] Source-specific parameters.
- [ ] Source-local levels, curves, contrast, blur, sharpen, and threshold.
- [ ] Source inversion and normalization.
- [ ] Source preview, reset, randomize, and provenance.
- [ ] Independent source resolution policy.

Global fabrication settings remain outside both source editors.

### 23.2 Mesh Self-Intersection Strategy

The structured heightfield validator now reports closure, edge ownership,
winding, volume, connectivity, Euler number, and degenerate faces. General
triangle self-intersection detection remains a separate release decision.

- [ ] Define the structured-grid self-intersection guarantee.
- [ ] Add an optional collision backend for sampled preview meshes.
- [ ] Report `not checked` explicitly when full collision testing is unavailable.
- [ ] Add synthetic intersection fixtures when a backend is available.

### 23.3 Heightmap Import Semantics

- [ ] Distinguish heightmap, mask, and image/luminance import modes.
- [ ] Preserve single-channel grayscale heightmaps without RGB conversion.
- [ ] Distinguish 8-bit and 16-bit normalized data.
- [ ] Expose linear-data versus sRGB interpretation where applicable.
- [ ] Store the selected interpretation in provenance.
- [ ] Add 8-bit, 16-bit, RGB, and RGBA import fixtures.

### 23.4 Explicit Project Layer Model

The supported V2 layer path is:

```text
Primary field → Secondary field → Mask → Composition → Final field
```

- [ ] Name primary, secondary, and mask sources in project summaries.
- [ ] Persist visibility and enabled state.
- [ ] Keep source-local processing separate from global mapping.
- [ ] Add a complete layer-path summary to the project/export view.
- [ ] Do not add unlimited arbitrary layers before this model is proven.

### 23.5 Pattern UI Scaling

- [ ] Group patterns into Terrain, Cellular, Geometric, Organic, Mathematical,
  Decorative, and Imported categories.
- [ ] Add searchable or filterable source selection.
- [ ] Add favorites/recent sources.
- [ ] Add compact pattern previews.
- [ ] Add source-specific help text.
- [ ] Add pattern-specific fabrication-risk hints.

### 23.6 Pattern-Specific Fabrication Warnings

- [ ] Voronoi: narrow cell boundaries and crack widths.
- [ ] Reaction-diffusion: isolated islands and tiny components.
- [ ] Cracks: disconnected lines and thin tips.
- [ ] L-systems: branch-tip thickness.
- [ ] Spectral fields: repetitive ridge concentration.
- [ ] Erosion: narrow channels and steep cuts.
- [ ] SDF Booleans: sharp intersections and tiny remnants.
- [ ] Chladni: thin nodal lines.

### 23.7 Export Reproducibility and Metadata

- [ ] Store the final export snapshot hash.
- [ ] Store source, processing, mapping, fabrication, and resolution metadata.
- [ ] Add metadata to 3MF where supported.
- [ ] Write optional STL sidecar metadata.
- [ ] Add a reproducibility summary to the export dialog.
- [ ] Add project-to-export regression coverage.

### 23.8 Recovery Semantics

- [ ] Distinguish normal and recovered projects.
- [ ] Distinguish recovered projects with embedded external fields.
- [ ] Explain when original source regeneration is impossible.
- [ ] Explain when only normalized embedded data is preserved.

### 23.9 Accessibility and Interaction Polish

- [ ] Verify keyboard focus order.
- [ ] Add accessible labels to source and fabrication controls.
- [ ] Keep units in every physical control label.
- [ ] Ensure warnings are not conveyed by color alone.
- [ ] Add keyboard shortcuts for collapse and cancel.
- [ ] Persist panel sizes and collapsed states.
- [ ] Provide high-contrast warning states.

### 23.10 Quality-Plan Non-Goals

Do not add these before the quality plan and release validation are complete:

- Unlimited field layers.
- General-purpose visual node editor.
- Sculpting brushes.
- Adaptive topology.
- Cloud generation.
- Ceramic firing compensation.
- Mold-release/draft analysis.
- Full CAD Boolean modeling.
