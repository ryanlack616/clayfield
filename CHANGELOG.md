# Changelog

## 2.0.0 - current development release

- Add QFractalNow `.config` sources rendered through the headless `fractalnow` command.
- Embed QFractalNow configuration text in portable ClayField projects.
- Add floating viewport previews, compose controls, and a camera-aware XYZ gizmo.
- Add validated 3MF/STL export workflows, fabrication controls, aspect-aware procedural resolution, and 2048-sample defaults.
- Refresh the Qt layout, source workflow, numeric controls, and fabrication panel.

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
- Current local validation passes 181 tests with 7 optional tests skipped.

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
