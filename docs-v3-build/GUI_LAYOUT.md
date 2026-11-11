# Clayfield — GUI Layout and Interaction Specification

**Document status:** Authoritative first-pass GUI specification  
**Target:** Existing PySide6 / Qt 6 desktop application  
**Primary workflow:** Single image → relief → analyze → mask → selective cleanup → mesh export

---

## 1. Product and UX goals

Clayfield is a focused image-to-relief engineering tool. The interface must make it easy to inspect small surface defects, identify them at a meaningful physical scale, and clean them selectively without damaging intentional geometry.

Priorities, in order:

1. Keep the model visible and easy to inspect.
2. Make physical dimensions and processing parameters explicit.
3. Make analysis understandable and previewable.
4. Make mask state visible, editable, reusable, and independent of geometry.
5. Make cleanup local, predictable, reversible, and mask-aware.
6. Make export straightforward while still validating the mesh.

The GUI is not a general-purpose node editor or procedural modeling environment.

## 2. Main window geometry

### Default geometry

| Element | Default |
|---|---:|
| Main window | 1600 × 1000 logical px |
| Preferred left source dock | 260 px |
| Preferred right settings dock | 360 px |
| Minimum viewport width target | 750 px |
| Interface density | Moderate |

The left and right widths are preferences, not hard-coded fixed widths. The user can resize, move, float, tabify, and hide docks. The source dock defaults to the left and should restore there after a reset-to-default-layout command. The settings dock defaults to the right.

### Window structure

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ [geometric mark] CLAYFIELD       File   Edit   View   Tools   Help             Project title  │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  ┌─────────────────────┐  ┌──────────────────────────────────────────┐  ┌──────────────────┐ │
│  │ SOURCE DOCK         │  │                                          │  │ SOURCE MODEL     │ │
│  │                     │  │                                          │  │                  │ │
│  │ Image preview       │  │                                          │  │ Image / relief   │ │
│  │                     │  │              PERSISTENT                  │  │ controls         │ │
│  │ Zoom / pan / fit    │  │              3D VIEWPORT                 │  │                  │ │
│  │                     │  │                                          │  │                  │ │
│  │ Source actions      │  │                                          │  │                  │ │
│  │                     │  │                                          │  │                  │ │
│  └─────────────────────┘  └──────────────────────────────────────────┘  └──────────────────┘ │
│                                                                                              │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│ Ready | 120 × 120 mm | 4.0 mm relief | 248,000 triangles | X 42.3  Y 67.8 | Valid | Tool: — │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

The right dock has horizontal workspace tabs at its top. The central viewport remains visible when tabs change. The main menu and status bar remain stable across workspaces.

## 3. Main menu and application chrome

### Menu bar

Use the familiar menu structure:

- **File:** New Project, Open Project, Save, Save As, Import Image, Export, Recent Projects, Exit.
- **Edit:** Undo, Redo, History, Preferences (if supported by current app structure).
- **View:** Show/Hide Docks, Reset Layout, Viewport Background, Grid, Ground Shadow, Camera Views, Fullscreen.
- **Tools:** Contextual commands for the active workflow; avoid duplicating every panel control.
- **Help:** Documentation, Shortcuts, About.

Do not invent project-file functionality if the current application does not have it. During the repository audit, distinguish existing commands from planned commands. If project save/load is not currently supported, mark it as a planned capability rather than exposing a nonfunctional menu item.

### Branding/title region

- Small geometric mark and `CLAYFIELD` wordmark at upper left.
- Project/document name may appear toward the right side of the title region or in the native window title, depending on current Qt window chrome.
- Do not build a tall branded header.

### Status bar

Compact, persistent, and information-dense. Show:

- Processing state / short progress text.
- Physical model dimensions.
- Relief depth or total thickness when relevant.
- Triangle count when a mesh exists.
- Cursor X/Y and sampled height when the pointer is over the model and inspection is available.
- Active tool.
- Mesh validation indicator when validation has been run.

Avoid showing stale values. If data is unavailable, show an em dash or a clear unavailable state, not a fabricated zero.

Progress feedback is primarily in the status bar. For operations that run long enough to need more detail, the status text may include percentage and an inline cancel affordance. Do not block the UI thread.

## 4. Docking and workspace behavior

- Use Qt dock widgets or the repository's existing docking mechanism; confirm actual implementation during audit.
- Left source dock defaults to the left; right settings dock defaults to the right.
- Both docks can be resized, floated, moved, tabified, hidden, and restored.
- Persist dock arrangement and visibility between sessions.
- Provide **View → Reset Layout** to restore defaults.
- Do not create multiple workspace-layout presets in the first release. One user-customizable layout is sufficient.
- Docking must not destroy the viewport or reset geometry/camera state.
- Respect a minimum useful viewport width target of 750 logical px where window dimensions permit. When the window is too small to honor all preferred widths, allow docks to shrink or collapse gracefully rather than forcing an unusable layout.

## 5. Persistent 3D viewport

The viewport is the primary working surface and remains visible across all five workspace tabs.

### Viewport overlays and controls

- Compact contextual floating tool palette appears when a viewport tool is active.
- Palette can be moved and pinned. When unpinned, it should remain unobtrusive and avoid covering the active target.
- Viewport toolbar/control groups should be available without becoming a permanent oversized bar.
- Controls include camera/view, display mode, grid, ground shadow, wireframe, analysis overlay, mask overlay, and camera reset.
- XYZ axis gizmo in a viewport corner; clickable axes align the camera. No orientation cube in the first release.

### Navigation

| Action | Default input |
|---|---|
| Orbit | Left mouse drag on empty viewport area |
| Pan | Middle mouse drag |
| Zoom | Scroll wheel |
| Frame model | `F` |
| Reset camera | `Home` |
| Toggle wireframe | `W` |
| Toggle grid | `G` |

These are proposed defaults. During implementation, check for conflicts with existing viewport bindings and text editing. Provide a shortcut reference in Help. Brush tools must take precedence over orbit only while the active brush tool is engaged and the pointer is over the model.

### Camera and framing

- Initial model view: three-quarter angle that shows both surface and relief depth.
- Frame model after first successful generation.
- Preserve the camera during workspace tab changes and parameter edits that do not invalidate the model.
- Camera reset returns to the standard three-quarter framing.
- Provide orthographic/perspective switching if supported by the existing renderer.

### Display modes

1. **Clay:** default matte technical gray material.
2. **Material:** selectable neutral clay/ivory material variants.
3. **Height:** height-based visualization.
4. **Wireframe:** inspect mesh density/topology.
5. **Analysis:** display analysis heatmap, either replacing clay or translucent overlay.
6. **Mask:** display editable/protected mask overlay.

Not every mode needs a separate rendering implementation if existing shaders can support combined modes. Preserve the current rendering pipeline where possible.

### Lighting and environment

- Default: one directional light with soft shadows.
- Expose a small number of controls for light direction and intensity.
- Grid and ground shadow are independently configurable.
- Default background is dark graphite; offer a small curated set of professional alternatives.
- Do not add a full studio-light rig or unrestricted background editor in the initial release.

### Surface inspection

Hovering over the model can display a compact readout in the status bar or a small viewport readout:

```text
X 42.35 mm   Y 67.82 mm   Height 3.42 mm   Slope 12.6°   Curvature 0.084
```

Rules:
- Coordinates and height must use the model's actual physical coordinate mapping.
- Slope is shown only if calculated from the current surface representation.
- Curvature is shown only when a defined curvature metric is available; label the metric and units/convention.
- Do not show placeholder or fabricated values.
- Provide an option to disable hover inspection if it becomes visually distracting.

## 6. SOURCE workspace

Purpose: load one source image, inspect it, and make source-level adjustments before relief generation.

### Panel hierarchy

```text
SOURCE
────────────────────────────────
[ Image preview area             ]
[ fit / 1:1 / zoom readout        ]

SOURCE IMAGE
Filename
Dimensions: W × H px
Color mode / alpha (when known)

IMAGE ADJUSTMENTS
Brightness        [numeric] [slider]
Contrast          [numeric] [slider]
Gamma             [numeric] [slider]
Invert            [toggle]

IMAGE TRANSFORM
Rotate left / right
Flip horizontal / vertical
Crop (if existing pipeline supports it)

[ Replace Image ]
[ Generate Relief → ]
```

### Preview behavior

- Adjustable preview with zoom and pan.
- Scroll wheel zoom; middle drag pan; Fit and 1:1 actions.
- Transparency uses a subtle checkerboard behind the image.
- Display original pixel dimensions and filename.
- Replace image without unintentionally clearing unrelated project preferences.
- Keep image preview independent of 3D viewport navigation.

### Source controls

- One active image at a time.
- Brightness, contrast, gamma, and invert are planned controls; bind them to actual processing capabilities after audit.
- Rotate/flip actions must have clear, reversible behavior.
- Crop is only exposed if the existing image pipeline supports a correct crop workflow; otherwise list it as a later task.
- Source changes that affect generated geometry must mark the relief as needing regeneration or show a clear stale-state indicator. Never silently leave the viewport appearing current when it is not.

### Empty state

When no image is loaded, show a clear drop/open target with supported file types and a concise instruction. Do not show a blank preview with unexplained disabled controls.

## 7. MODEL workspace

Purpose: define physical output dimensions and generate the relief.

### Panel hierarchy

```text
MODEL
────────────────────────────────
PHYSICAL SIZE
Width                  [120.0] mm
Height                 [120.0] mm
[ ] Lock aspect ratio

RELIEF
Maximum relief depth   [4.0] mm
Base thickness         [2.5] mm
Invert height          [toggle if supported]

RESOLUTION
Mesh density           [quality control]
Target spacing         [value + unit, if supported]
Estimated triangles    [read-only estimate]

[ Generate / Update Relief ]
```

### Behavior

- Direct numeric entry is mandatory for physical dimensions and thickness.
- Units are visible beside values.
- If aspect ratio is locked, changing one dimension updates the other based on the source image ratio.
- Display the estimated mesh size only if the estimator is based on actual sampling/resolution logic.
- Clearly distinguish source pixel resolution, heightfield sampling resolution, and final mesh triangle count.
- Generation runs asynchronously where practical and reports progress in the status bar.
- On successful generation, frame the model in the viewport.
- If parameters change after generation, mark the model as out of date until regenerated.

## 8. SURFACE workspace

Purpose: inspect surface characteristics at selected physical scales and create a weighted mask.

### Analysis methods

The methods must be technically distinct, not merely alternate names for one filter:

1. **Detail Size:** identify features within a selected physical size range.
2. **Surface Roughness:** measure small-scale height fluctuations relative to a defined local scale.
3. **Surface Irregularity:** identify locally inconsistent surface geometry using a defined neighborhood/metric.
4. **Curvature:** identify changes in surface direction using a documented curvature measure.
5. **Isolated Peaks:** detect localized protrusions relative to their neighborhood.
6. **Depressions:** detect localized pits or recesses relative to their neighborhood.
7. **Edge Protection:** identify strong boundaries or transitions that should be protected.
8. **Combined Detection:** combine selected methods using simple ANY/ALL logic.

During implementation, each method must have a documented mathematical definition, input representation, physical scale interpretation, and expected output. Do not expose a method until its metric is implemented and tested.

### Panel hierarchy

```text
SURFACE
────────────────────────────────
ANALYSIS METHOD
[ Surface Irregularity             ▼ ]

SCALE RANGE
Minimum                 [0.20] mm
Maximum                 [0.80] mm

SENSITIVITY
[ numeric ] [slider]

METHOD PARAMETERS
[ method-specific controls ]

PREVIEW
Detected area           12.4 %
Severity / metric       [method-specific]
[ ] Show legend
[ ] Show numerical values

DISPLAY
(•) Heatmap   ( ) Clay overlay
[ ] Protect strong edges

[ Preview Analysis ]
[ Generate Mask ]
```

### Scale-aware analysis

- Physical scale is central to the product. Express scale in millimeters where the underlying sampling supports a valid physical mapping.
- Allow a minimum and maximum feature scale where relevant.
- Example scales such as 0.1–0.3 mm, 0.3–0.75 mm, 0.75–2 mm, and 2–5 mm may be offered as starting presets only after validated against the actual sampling density. They are not universal definitions.
- Distinguish feature size from roughness amplitude. A feature can be small but smooth; a larger feature can be rough.
- Avoid classifying intentional ridges or edges as defects solely because their slope is high.
- Report when the requested scale is below the effective spatial resolution of the source/heightfield/mesh.

### Preview and mask creation

- Preview analysis without modifying geometry or mask.
- Show the active metric, its units/convention, scale range, and legend.
- User explicitly chooses Generate Mask to create/update the mask.
- Analysis output is converted to a standardized weighted mask where applicable.
- Combined Detection initially supports simple ANY and ALL composition. No node editor or arbitrary rule builder.

## 9. Mask model and visualization

The mask is independent data, not a destructive geometry edit.

### Weight convention

- `1.0` / white-equivalent: fully eligible for cleanup.
- `0.0` / black-equivalent: protected.
- Intermediate values: partial influence.

UI color convention:
- Cyan: eligible region.
- Dark gray: protected region.
- Intermediate weights: controlled opacity/intensity between the two states.

### Required mask operations

- Replace
- Add
- Subtract
- Invert
- Expand
- Contract
- Feather
- Threshold
- Clear
- Manual paint
- Manual erase

Mask operations must preserve a predictable weight interpretation. The exact morphology implementation depends on the authoritative geometry/sampling representation found in the audit.

### Representation requirement

Choose and document one authoritative mapping between mask samples and the geometry being edited. If the application uses a heightfield, align mask samples to the heightfield. If cleanup acts on a mesh, define a stable mapping from mask samples to mesh vertices or surface samples. Do not silently mix representations or let a resample shift the mask relative to the geometry.

### Mask UI behavior

- Show/hide overlay independently of mask activation.
- Opacity control.
- Clear indication when no mask exists, when a mask is stale, and when it is active.
- Reuse the same mask across multiple cleanup operations.
- Undo/redo includes mask edits.
- Geometry regeneration that invalidates the mapping must mark the mask stale or explicitly regenerate/remap it; never silently apply a misaligned mask.

## 10. CLEANUP workspace

Purpose: selectively improve the surface while preserving intentional geometry.

### Panel hierarchy

```text
CLEANUP
────────────────────────────────
ACTIVE TOOL
[ Smooth ▼ ]

BRUSH
Radius                  [1.00] mm
Strength                [0.50]
Falloff                 [Soft ▼]
Flow                    [0.50]
[ ] Advanced cursor info

OPERATION
Method                  [Bilateral ▼]
Iterations              [value if relevant]
Preserve edges          [toggle if supported]

MASK
[✓] Respect active mask
[ Show mask overlay ]
[ Edit mask ]

PREVIEW / COMMIT
[ Preview ] [ Apply ] [ Cancel ]

HISTORY
Original Relief
Surface Analysis
Mask Generated
Bilateral Smoothing
Manual Cleanup
```

### Cleanup operations

Initial candidate operations:
- Smooth
- Remove Noise
- Reduce Detail
- Sharpen
- Flatten
- Fill Depressions
- Reduce Peaks

Prioritize a small, reliable subset for the first usable release: mask-aware smoothing, median/spike cleanup, and noise reduction. Add the remaining operations only when their behavior is well-defined and validated.

### Brush tools

- Smooth
- Relax
- Flatten
- Polish
- Restore Original Surface

Brush parameters:
- Radius in mm.
- Strength.
- Falloff.
- Flow.
- Spacing if the stroke engine needs it.
- Optional tablet pressure support only if the input stack supports it reliably.

Normal brush cursor shows circle and falloff. Advanced mode adds center and strength information.

### Mask-aware cleanup behavior

- Cleanup respects the active mask by default.
- Protected regions must not be modified by a cleanup operation when mask restriction is enabled.
- Brush strokes crossing protected regions must attenuate or stop according to mask weights.
- Provide an explicit, clearly visible way to disable mask restriction temporarily.
- Preview before Apply; Cancel must restore the pre-preview state.
- Keep the mask reusable after geometry cleanup.
- Preserve an original surface reference for the Restore Original Surface brush, with a clearly defined lifetime and memory strategy.

Conceptual blend:

`result = original × (1 − influence) + processed × influence`

where `influence = mask_weight × brush_weight × operation_strength` (with normalized/clamped weights). The actual algorithm must respect the geometry representation and avoid repeated resampling artifacts.

### Smoothing algorithm distinction

- Gaussian: general blur; may soften edges and shrink features.
- Bilateral: smooth local variation while preserving strong edges; parameters must have clear spatial and height/range meaning.
- Median: robust removal of isolated spikes/outliers.
- Taubin: mesh smoothing intended to reduce shrinkage compared with basic Laplacian smoothing; applies to mesh topology, not directly interchangeable with heightfield filters.
- HC Laplacian / Relax: later mesh-focused options if needed.

Do not present heightfield filters and mesh-topology algorithms as interchangeable options without explaining which geometry representation they operate on.

### Before/after inspection

Provide:
- Before/after toggle.
- Split comparison if feasible.
- Difference visualization for geometry changes.
- Analysis heatmap and mask overlay toggles.
- Cross-section inspection and height histogram as later enhancements, not blockers for first release.

## 11. OUTPUT workspace

Purpose: export a validated physical mesh.

### Panel hierarchy

```text
OUTPUT
────────────────────────────────
FORMAT
(•) STL   ( ) 3MF

FILE
[ filename / destination ]
[ Browse ]

MODEL SUMMARY
Width                  120.0 mm
Height                 120.0 mm
Total thickness          6.5 mm
Triangles              248,000

VALIDATION
Watertight             ✓
Non-manifold edges      0
Isolated components     0
Minimum feature size    [value / status if computed]

[ Export ]

ADVANCED SETTINGS  [expand]
[ format-specific options ]
```

### Export behavior

- Simple export by default: choose STL or 3MF, filename/destination, Export.
- Advanced settings expand only when needed.
- Show physical dimensions, total thickness, and triangle count when available.
- Validate watertightness, non-manifold edges, and isolated components when supported by the mesh tooling.
- Minimum wall thickness and minimum feature size are later validation capabilities unless the current pipeline can compute them reliably.
- Report validation results honestly. Do not show a green valid state if a check was not run.
- Export should not mutate the working geometry.

## 12. Undo, history, and operation lifecycle

- Standard Undo/Redo actions and keyboard shortcuts.
- Dedicated history panel accessible from Edit or the CLEANUP workspace.
- History entries use meaningful operation names and timestamps or ordering indicators.
- Selecting an entry should inspect/preview that state without silently discarding later work.
- Every destructive operation has a defined preview/commit/cancel lifecycle.
- Undo/redo must account for geometry and mask edits. Avoid a split history that can restore incompatible states.
- Establish memory limits and snapshot/delta strategy after auditing mesh sizes and existing implementation.

## 13. Workspace persistence

When switching tabs:
- Keep the viewport visible.
- Preserve each workspace's scroll position.
- Preserve selected analysis method and its parameters.
- Preserve mask display/opacity preferences.
- Preserve brush selection and brush parameters.
- Preserve panel docking arrangement and sizes.
- Use a subtle transition only; do not delay interaction.

One customizable workspace is sufficient initially. Save the layout between sessions and provide Reset Layout.

## 14. Empty, loading, stale, and error states

Design explicit states for:

- No source image loaded.
- Image loaded, relief not generated.
- Relief generated and current.
- Relief stale because source or model parameters changed.
- Analysis not run / preview available / completed / failed.
- No mask / active mask / stale mask.
- Cleanup preview running / ready to apply / cancelled / failed.
- Mesh not generated / generated / validation pending / valid / invalid.
- Export running / completed / failed.

Use clear status text and actionable recovery. Do not leave controls enabled when prerequisites are missing unless they have a clear explanation.

## 15. Keyboard shortcuts

Proposed initial defaults; verify against existing bindings and text-edit behavior:

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open image/project (depending on supported project model) |
| `Ctrl+S` | Save project (only if project persistence exists) |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `F` | Frame model |
| `Home` | Reset camera |
| `W` | Toggle wireframe |
| `G` | Toggle grid |

Brush-specific shortcuts (radius adjustment, tool selection) should be added only after the core interaction model is tested. Do not steal common text-entry keys while a text field has focus.

## 16. Responsive and high-DPI behavior

- Dimensions are logical pixels.
- Support high-DPI scaling.
- At narrower window sizes, dock panels may shrink/collapse; viewport remains usable.
- Do not force the preferred 750 px viewport width when the total window width makes it impossible.
- Test 1600 × 1000 default and at least one smaller supported size.
- Ensure floating palette and viewport gizmo remain within visible viewport bounds.

## 17. Definition of GUI completion

The GUI first pass is complete when:

- The main window, menus, docks, tabs, persistent viewport, and status bar are implemented.
- Docks can be resized, moved, floated, hidden, restored, and persisted.
- All five workspaces have complete layout and state behavior, even if some advanced tools are visibly marked as not yet implemented during staged development.
- Viewport navigation, camera framing, display modes, grid, shadow, and axis gizmo work.
- Controls have consistent visual styling, units, focus, disabled, hover, and tooltip behavior.
- Workspace state persists across tab switches.
- No placeholder status values or nonfunctional controls are presented as completed features.
- Existing geometry and rendering behavior remains intact.
