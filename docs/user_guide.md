# ClayField user guide

## Create a relief

1. Choose a primary source in the Source selector. Available sources include
   images, deterministic procedural generators, and **QFractalNow config**.
   For an image, use **Load Image** or drag it onto the image panel. For
   QFractalNow, choose **Load QFractalNow Config…** and select a `.config` file.
   Images load asynchronously and convert to grayscale; procedural sources
   generate from their stored parameters and seed.
2. Optionally set crop margins and an image resize. The source remains intact.
   Adjust the image levels, tone curve, brightness, contrast and filters.
   **Invert** changes image intensity; the independent terrain mapping curve
   changes the relationship between intensity and physical height.
3. Set width, depth, minimum and maximum height, and base thickness in
   millimeters. The width/depth lock follows the cropped/resized aspect ratio;
   procedural sources use the physical width/depth ratio for their sample grid.
   Height inversion is separate from image inversion; normalize, clamp, scale,
   and offset affect the physical mapping. Smoothing, edge falloff, and
   reproducible multi-octave noise have independent strength controls.
4. Orbit with left drag, pan with middle drag, and zoom with the wheel. The View
   menu contains camera presets, fit, wireframe, height coloring, lighting and
   surface color, grid visibility, orthographic projection, and a dark theme.
   Undo/redo and portable adjustment/terrain presets are in the Edit menu.
5. Choose original, adjusted, or final-heightmap preview from **PROCESS**; save a `.clayfield`
   project or export STL, 3MF, or a PNG/TIFF heightmap. The export dialog shows
   dimensions, an estimated minimum wall, and sampled mesh validation.
6. Use **View > Cross-section** to inspect a width or depth profile, its physical
   distance, minimum/maximum height, and relief range.

Image and heightfield adjustments run in the background. Export requires the
current image adjustment to finish; exports check for cancellation between stages
and during chunked mesh and file writing. Large solid meshes use
substantial memory: the terrain panel shows an estimate and the exporter rejects
work estimated above its safety limit. Lower the export resolution if necessary.

## Physical output

Positive relief rises above the base; negative relief recesses into the base.
The maximum recess must be less than the base thickness. STL and 3MF models are
rotated to Z-up and placed on the build plate. The internal coordinate system is
X width, Y height, Z depth. Heightmaps are normalized to the actual minimum and
maximum of the exported heightfield, so they do not encode absolute millimeters.

PNG/TIFF source pixels are retained at 8- or 16-bit precision where supported.
Transparency is retained in project files but ignored when calculating luminance.
Project files embed a lossless copy of the source. Recovery snapshots are saved
periodically while a project has unsaved changes and offered when restarting.

## Procedural and external image sources

V2 procedural sources are generated locally with deterministic Python/NumPy
components. Noise, wave interference, and Mandelbrot fields do not require a
neural network or a GPU. Their parameters, seeds, and algorithm
versions are stored in the project so the field can be regenerated.

QFractalNow `.config` files are embedded in the project. ClayField uses the
headless `fractalnow` command to regenerate them at preview and export
resolution. Install FractalNow and ensure `fractalnow` is on `PATH` before
opening a project that contains a QFractalNow source.

External image tools may generate or process a heightmap or mask. Export the
result as an image, then use ClayField's **Import Secondary Heightmap** or
**Import Mask** controls. ClayField validates and processes the imported data
deterministically before physical mapping and export. ClayField does not
include an in-app external image-generation service.

For digital print QA, run `benchmarks/print_qa.py` with
`CLAYFIELD_PRUSA_SLICER` set. It generates both mesh formats, records slicer
dimensions/manifold status, and produces G-code. Physical printing still needs
to be performed on the target printer.

## Troubleshooting

If OpenGL initialization fails, verify that the driver supports OpenGL 3.3.
On systems with conflicting GNOME theme settings, launching with
`QT_STYLE_OVERRIDE=Fusion QT_QPA_PLATFORM=xcb` may help. Disable **GPU Image
Preview** from the View menu if the optional preview processing encounters a
driver issue; CPU processing and export remain available.
