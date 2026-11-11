# Changelog

## 2.0.0 - current development release

- Add QFractalNow `.config` sources rendered through the headless `fractalnow` command.
- Embed QFractalNow configuration text in portable ClayField projects.
- Add floating viewport previews, compose controls, and a camera-aware XYZ gizmo.
- Add validated 3MF/STL export workflows, fabrication controls, aspect-aware procedural resolution, and 2048-sample defaults.
- Refresh the Qt layout, source workflow, numeric controls, and fabrication panel.
- Validate image dimensions, modes, and precision from the Pillow header before
  decoding, and enforce a shared, configurable allocation budget for image
  loading, archive members, heightfields, and mesh export.
- Read archive members into one bounded buffer and decode embedded images
  through the same validated loader instead of an unchecked `cv2.imdecode`.
- Warn or fail on generator workloads that exceed the soft and hard work limits,
  and suggest a resolution that fits the CPU budget when an export is refused.
- Decimate the viewport display texture with an area-averaged box filter and
  sample the histogram after downsampling so large images stay interactive.
- Cache external-field wrappers until the field changes, avoid redundant
  full-resolution copies in field and mesh pipelines, and move the shared
  cancellation primitive into `clayfield.core` so leaf modules stay Qt-free.
- Add a surface-aware sculpt brush with adjustable radius, strength, falloff, and
  Laplacian, Taubin, and bilateral smoothing modes. Dabs are spaced by arc length
  along the pointer path, so stroke strength is independent of pointer speed.
- Pick the brush centre by ray casting the visible heightfield, and draw the brush
  cursor as a world-space ring sampled from the same surface.
- Store sculpt work as a displacement layer over the procedural base so terrain
  parameter changes keep the sculpt, and persist the layer inside `.clayfield`
  projects as a sparse compressed member. Discard the layer explicitly when the
  heightfield resolution changes.
- Undo and redo sculpt strokes at stroke granularity through an edit ledger that
  orders parameter snapshots and sculpt strokes chronologically, so mixed edits
  undo and redo in the order they were made.
- Track sculpt changes against the last saved layer so a parameter undo cannot
  mark saved sculpt work clean. The comparison allows float32 rounding, so
  undoing a stroke back onto the saved layer clears the dirty marker instead of
  leaving the title marked as changed.
- Add a close button to the sculpt overlay and a `View → Sculpt Brush` toggle
  (`Ctrl+B`), so the brush controls can be dismissed instead of covering the
  canvas permanently. Right-drag orbits while the brush owns the left button.
- Start the sculpt overlay hidden and make `View → Sculpt Brush` the entry
  point: opening it arms the brush and closing it disarms. A 250 px card used to
  cover the bottom-left corner of the canvas before any geometry existed. The
  `Brush` combo still parks the brush while the panel stays open.
- Anchor the sculpt overlay from the viewport's own resize event and settle its
  layout height first; it previously kept a position computed from the parent's
  stale viewport size and floated mid-canvas.
- Guard the sculpt layer against a shape mismatch on press, so a layer from a
  different grid is discarded with a status message instead of raising inside
  the stroke session.
- Start the viewport with height coloring on and the construction grid hidden,
  and read both View-menu check marks from the viewport instead of hardcoding
  them. A flat surface colour hid the relief and the grid competed with it.
- Add `View → Height Colors…`, a two-swatch ramp editor with a live gradient
  preview. The fragment shader now takes `height_low_color` and
  `height_high_color` uniforms instead of hardcoded endpoints, so the whole
  height ramp is user-selectable.
- Switch height coloring back on when a ramp is chosen and off when a flat
  surface colour is chosen, so each colour dialog shows its own result instead of
  changing a value the viewport ignores.
- Read the `View → Dark Theme` check mark from the saved setting instead of
  hardcoding it on. A fresh install starts with the light palette, so the menu
  used to claim a theme the window was not using.
- Divide the Laplacian by the neighbour count in the Laplacian and Taubin
  smoothing kernels. The raw stencil's largest eigenvalue is 8, so a full-strength
  dab multiplied the highest-frequency component by `1 - 8*lambda` and grew the
  surface by orders of magnitude per dab until the mesh left the viewport and the
  driver stalled. Reject non-finite or non-positive `lambda`/`mu` and Taubin pairs
  that violate the passivity condition `1/lambda + 1/mu > 0`.
- Remove the `COMPOSE ▸` section toggle from the bottom of the left panel. The
  compose controls live in a floating overlay, so `View → Compose…` opens it and
  its own `×` closes it. The sidebar now ends on the PROCESS controls instead of
  a header below a stretch.

## V2 development status

- Add deterministic procedural field sources including multiscale noise, waves,
  Mandelbrot, Voronoi, ridged/warped noise, SDF shapes and Booleans, Chladni,
  spectral, reaction-diffusion, phyllotaxis, cellular automata, flow, erosion,
  branching, cracks, Penrose-style, and Truchet-style fields.
- Add normalized field composition, masks, physical mapping, fabrication profiles,
  final export-resolution analysis, and external heightmap/mask interchange.
- Add schema version 4 projects, procedural sources, recovery, worker
  cancellation, provenance, source summaries, deterministic sample artifacts,
  and calibration artifact generation.
- Current local validation passes 250 tests with 7 optional tests skipped.

## 0.3.0

- Add non-destructive image crop and resize, height mapping controls, fractal
  noise, modifier strengths, presets, and image/heightmap comparison.
- Add orthographic projection, grid visibility, dark theme, parameter sliders
  and reset controls, and export preview with sampled mesh validation.
- Implement GPU blur and sharpen and direct GPU-to-viewport previews; keep CPU
  processing authoritative for saved output.
- Debounce edits, cache image-processing stages, improve export cancellation,
  and migrate version 1/2 projects to the version 3 format.
- Exercise GPU/CPU agreement on NVIDIA and Mesa software rendering.
- Add cross-section inspection and a repeatable PrusaSlicer print-QA artifact.

## 0.2.0

- Repair OpenGL initialization across Qt EGL/GLX configurations and add GPU
  tonal previews with CPU reference checks.
- Add undo/redo, background image loading and autosave, and safer recovery.
- Rotate printable STL and 3MF exports onto the Z-up build plate; verify both
  formats with PrusaSlicer and 3MF with lib3mf.
- Improve mesh construction, memory estimates, viewport navigation and normals,
  export progress, recent projects, and 8/16-bit heightmap output.
- Add a Linux bundle specification, clean-install checks, and integration and
  stress tests.
