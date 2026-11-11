# Clayfield — Implementation Roadmap

**Purpose:** Turn the approved GUI/product direction into an incremental, low-risk engineering plan.  
**Architecture constraint:** Preserve the current PySide6 / Qt 6 and OpenGL implementation where practical.  
**Planning rule:** Repository audit first; implementation decisions must be based on observed code, not assumptions.

## Product outcome

A focused desktop tool that converts one image into a physical 3D relief, identifies scale-specific surface irregularities, generates an editable weighted mask, performs selective cleanup, and exports a validated STL/3MF mesh.

## Guiding principles

1. Audit before editing.
2. Preserve working code and dependencies.
3. Keep UI, analysis, mask, and geometry responsibilities separated where the current architecture allows.
4. Establish one authoritative geometry representation and one well-defined mask mapping.
5. Build the smallest end-to-end vertical slice before adding every analysis/cleanup feature.
6. Make destructive processing previewable, cancellable where safe, and undoable.
7. Measure performance on representative real projects, not only tiny fixtures.
8. Do not add architecture or configuration layers without a demonstrated need.

---

## Phase 0 — Repository audit and baseline

### Objectives

Understand the current application, verify working behavior, and identify the smallest path to the new GUI.

### Audit areas

- Repository structure and launch entry point.
- Python version, dependency manager, Qt/PySide6 version.
- Main window, current panels, menus, settings persistence.
- Existing QOpenGLWidget or other viewport implementation.
- Camera, lighting, materials, overlays, and input bindings.
- Image loading and preprocessing.
- Heightfield creation and physical dimension mapping.
- Mesh generation, topology, and Trimesh use.
- Current geometry representation at each processing stage.
- Existing undo/redo or snapshot mechanisms.
- STL/3MF export and validation.
- Tests, fixtures, sample assets, logging, and error handling.

### Deliverables

- `REPOSITORY_AUDIT.md` with exact paths and verified facts.
- Current workflow diagram or concise sequence.
- Inventory of reusable components.
- Known gaps and risks.
- Baseline run/test instructions and results.

### Exit gate

Do not begin structural UI changes until the current application can be launched (or its launch failure is documented), the viewport path is understood, and geometry/mask representation choices can be made from evidence.

---

## Phase 1 — Architecture decisions and UI shell

### Objectives

Build the new application frame without rewriting the geometry or rendering pipeline.

### Work

- Define main-window composition using the existing Qt patterns.
- Implement or adapt dockable source and settings panels.
- Add workspace tabs: SOURCE, MODEL, SURFACE, CLEANUP, OUTPUT.
- Keep the existing 3D viewport persistent in the center.
- Add compact main menu and status bar.
- Add workspace persistence and Reset Layout.
- Apply design tokens and common controls.
- Preserve existing viewport interactions while integrating the new chrome.

### Deliverables

- Main application shell.
- Dockable panels and tabbed settings area.
- Visual theme and shared widgets.
- Basic interaction tests for dock behavior and state persistence.

### Exit gate

At 1600 × 1000 logical px, the shell is visually coherent, panels dock correctly, viewport remains active across tabs, and existing model display still works.

---

## Phase 2 — SOURCE and MODEL vertical slice

### Objectives

Complete the input-to-relief workflow through the new interface.

### Work

- Source image empty state, file selection, preview, zoom, pan, fit, and metadata.
- Bind source adjustments only to existing or implemented processing operations.
- Physical width/height, aspect ratio, relief depth, base thickness, and resolution controls.
- Explicit stale state when source/model parameters change.
- Asynchronous generation/progress where supported by current architecture.
- Frame generated model in viewport.

### Exit gate

A user can load one image, inspect it, define physical dimensions, generate a relief, and see correct physical dimensions in the UI and exported geometry.

---

## Phase 3 — Geometry and mask contract

### Objectives

Resolve the central technical dependency before implementing advanced analysis.

### Required decisions

These are recorded in [`MEASUREMENT_SPEC.md`](MEASUREMENT_SPEC.md) §1–§2 rather than re-derived here. The audit's answers are adopted; this phase implements them and proves them with tests.

- Authoritative editable representation: heightfield, mesh, or a documented hybrid with clear ownership.
- Physical coordinate mapping from source pixels to model millimeters.
- Mask sampling domain and mapping to the editable geometry.
- Behavior when geometry is regenerated or resampled.
- Snapshot/delta strategy for undo and restore-original behavior.

### Work

- Define mask as a weighted field independent from geometry.
- Implement mask storage and mapping.
- Implement show/hide overlay and cyan/dark-gray visualization.
- Implement core mask operations: replace, add, subtract, invert, clear.
- Add mask stale-state detection.
- Add tests for alignment, resampling, bounds, and protected-region behavior.

### Exit gate

A mask can be created, visualized, edited, persisted for the current session, and mapped to the target geometry without drift. Geometry regeneration cannot silently apply a stale mask.

---

## Phase 4 — First analysis and mask workflow

### Objectives

Deliver a useful analysis-to-mask workflow with a small number of technically defensible methods.

### Recommended first methods

1. Detail Size.
2. Surface Roughness.
3. Surface Irregularity.
4. Isolated Peaks.
5. Depressions.
6. Edge Protection.

Curvature and Combined Detection follow after the first methods have verified metrics and UX.

### Work

- Implement each metric per [`MEASUREMENT_SPEC.md`](MEASUREMENT_SPEC.md) §3; the definition, units, parameters, and validity floor are fixed there.
- Validate each metric against the calibrated fixture in `MEASUREMENT_SPEC.md` §4, not only against a hand-inspected model.
- Validate scale limits against actual sample spacing.
- Implement preview that does not mutate geometry or mask.
- Display heatmap as replacement and translucent overlay.
- Convert analysis result into weighted mask.
- Show metric legend, scale range, and detected-area summary where meaningful.
- Add ANY/ALL combined detection later, with explicit input method selection.

### Exit gate

At least one analysis method reliably detects a known test feature at a known physical scale, previews the result, and creates a correctly aligned weighted mask.

---

## Phase 5 — Mask editing and selective cleanup

### Objectives

Deliver the defining product capability: clean unwanted local defects while protecting surrounding geometry.

### Work

- Manual paint and erase.
- Expand, contract, feather, threshold.
- Brush cursor with radius/falloff visualization.
- Contextual floating palette, movable and pinnable.
- Full controls in CLEANUP panel.
- Bilateral smoothing for edge-preserving heightfield cleanup if representation permits.
- Median/spike removal and noise removal as validated operations.
- Preview, Apply, Cancel.
- Mask-aware influence blend.
- Before/after toggle and operation history.
- Undo/redo across geometry and mask changes.

### Exit gate

A test surface with a known defect can be analyzed, masked, manually adjusted, cleaned, and compared. Protected areas remain unchanged within defined numerical tolerance. Undo restores the previous state.

---

## Phase 6 — OUTPUT and fabrication validation

### Objectives

Make export reliable and understandable.

### Work

- STL and 3MF selection.
- Filename/destination and simple export path.
- Expandable advanced options.
- Dimensions, total thickness, triangle count.
- Watertight, non-manifold, and connected-component checks where supported.
- Accurate validation status: distinguish passed, failed, not run, and unsupported.
- Export must not mutate working geometry.

### Exit gate

Representative models export successfully; dimensions are correct; validation results are truthful; re-imported output matches expected bounds and topology.

---

## Phase 7 — Polish, performance, and release hardening

### Work

- High-DPI and window-size testing.
- Dock persistence and reset behavior.
- Keyboard shortcuts and focus behavior.
- Tooltip coverage and accessibility review.
- Empty, loading, stale, failed, and completed states.
- Performance tests on large source images and dense meshes.
- Memory profiling for history and original-surface storage.
- Crash recovery / project persistence only if in scope and supported by existing architecture.
- Packaging and clean-environment launch test.

### Exit gate

No known blocker in the core workflow; UI remains responsive; long operations do not freeze the event loop; errors are actionable; all release-critical tests pass.

---

## Dependency map

```text
Repository audit
      │
      ▼
Application shell ───────────────┐
      │                           │
      ▼                           ▼
SOURCE + MODEL workflow       Existing viewport integration
      │                           │
      └──────────────┬────────────┘
                     ▼
             Geometry/mask contract
                     │
                     ▼
             Analysis → weighted mask
                     │
                     ▼
             Mask editing + cleanup
                     │
                     ▼
             OUTPUT + validation
                     │
                     ▼
             Polish / release
```

## Risks and mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Unknown existing architecture | UI rewrite could break working geometry/rendering | Read-only audit and baseline first |
| Ambiguous geometry ownership | Analysis and cleanup may operate on different representations | Define authoritative representation and conversion boundaries |
| Mask/mesh misalignment | Cleanup could damage unintended regions | Explicit mapping contract and alignment tests |
| Scale below sampling resolution | False precision and misleading detection | Report effective resolution; reject or warn on unsupported scales |
| Overloaded UI | Too many visible technical controls | Group controls with headings, preserve visible essentials, use advanced subsections only where useful |
| Long processing blocks Qt | Frozen interface | Worker/task pattern compatible with current architecture; status progress and safe cancellation |
| Undo memory growth | Dense meshes and snapshots can consume RAM | Profile and choose snapshot/delta strategy based on real project sizes |
| False validation confidence | UI could label untested geometry as valid | Distinguish pass/fail/not-run/unsupported |

## Scope control

Do not implement all eight analysis methods and all cleanup algorithms before a single end-to-end mask-aware cleanup workflow works. The first milestone is one reliable analysis → mask → selective cleanup path, not maximum feature count.
