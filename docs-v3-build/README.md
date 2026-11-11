# Clayfield — GUI Handoff Package

**Status:** Phase 0 repository audit complete; implementation planning next  
**Product:** Clayfield, single-image-to-3D-relief desktop application — the active product (ADR-0002)  
**UI framework direction:** Preserve the PySide6 / Qt 6 viewport, image pipeline, mask data model, and Trimesh export path. The audit proves the current window shell must be rebuilt, so Phase 1 replaces the splitter layout rather than restyling it.

## Package contents

| File | Purpose |
|---|---|
| `GUI_LAYOUT.md` | Authoritative screen, panel, viewport, control, and interaction specification |
| `VISUAL_DESIGN.md` | Visual identity, design tokens, component styling, iconography, and visual states |
| `IMPLEMENTATION_ROADMAP.md` | Ordered engineering phases, dependencies, risks, and acceptance gates |
| `TASK_LIST.md` | Actionable implementation checklist with completion criteria |
| `REPOSITORY_AUDIT.md` | Phase 0 read-only audit: verified paths, facts, gaps, risks |
| `MEASUREMENT_SPEC.md` | Proposed measurement layer: metric definitions, mask contract, calibrated fixture. Adopt or amend before Phase 3 starts. |

## Product definition

Clayfield converts **one source image** into a physical 3D relief that can be inspected, refined, and exported. Its defining capability is scale-aware surface inspection and selective cleanup: detect small unwanted irregularities, create a weighted mask, and refine eligible regions without damaging protected geometry.

The core workflow is:

1. Load and inspect one image.
2. Adjust image interpretation and physical relief parameters.
3. Generate and inspect the relief in the persistent 3D viewport.
4. Analyze surface characteristics at a selected physical scale.
5. Generate and edit a weighted mask.
6. Apply mask-aware cleanup and inspect before/after differences.
7. Validate and export STL or 3MF.

## Non-goals

The first implementation does not include a generator library, multiple simultaneous source inputs, a node editor, procedural source composition, or a general-purpose sculpting suite. These are intentionally excluded from the initial product scope.

## Non-negotiable engineering principles

- Audit the existing repository before changing code. Do not assume file names, class names, module boundaries, or current implementation details.
- Preserve working PySide6 / Qt 6, OpenGL, image-processing, and Trimesh components where practical.
- Do not rewrite the rendering or geometry pipeline merely to match the proposed UI.
- Keep the 3D viewport persistent while workspace content changes.
- Keep the weighted mask independent from geometry and retain it across compatible cleanup operations.
- Make physical units explicit wherever a parameter represents physical size or distance.
- Make destructive operations previewable, undoable, and clearly committed.
- Avoid silent changes to geometry, masks, or project settings.
- Keep the initial implementation incremental and testable.

## Source-of-truth hierarchy

1. Existing code and tests establish what is currently implemented.
2. `GUI_LAYOUT.md` establishes intended user-visible behavior.
3. `VISUAL_DESIGN.md` establishes visual tokens and component appearance.
4. `MEASUREMENT_SPEC.md` establishes the measurement math: metric definitions, mask contract, fixture. Status is *proposed* until adopted.
5. `IMPLEMENTATION_ROADMAP.md` establishes implementation order and architecture constraints. Phase gates live there only.
6. `TASK_LIST.md` tracks actual completion. A checkbox is checked only after its acceptance criteria are verified.

If an implementation constraint conflicts with this specification, document the conflict and propose the smallest safe adjustment. Do not silently invent a new architecture.

## First action for the coding agent

**Done.** The read-only repository audit is complete and recorded in
[`REPOSITORY_AUDIT.md`](REPOSITORY_AUDIT.md): entry point, main window, docks,
viewport, image pipeline, heightfield/mesh representations, undo/redo, settings
persistence, export path, tests, and dependencies. Phase 0 is closed in
[`TASK_LIST.md`](TASK_LIST.md). Start Phase 1 from the verified facts in the audit;
do not re-derive them.
