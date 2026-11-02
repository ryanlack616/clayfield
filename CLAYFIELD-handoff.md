# CLAYFIELD
## Complete Product Specification and Development Roadmap

**Project:** ClayField
**Description:** Image-to-heightfield and 3D relief generation software
**Platform:** Linux, initially Ubuntu
**Language:** Python 3.12+
**GUI:** PySide6 / Qt 6
**Rendering:** OpenGL 3.3 Core or newer
**GPU processing:** GLSL shaders
**Image processing:** OpenCV and NumPy
**Numerical processing:** NumPy and SciPy
**Mesh generation:** NumPy and Trimesh
**Testing:** Pytest
**License:** MIT

---

# PART 1 — PROJECT DEFINITION

## 1.1 What is ClayField?

ClayField is an open-source Linux desktop application that converts ordinary images into editable three-dimensional heightfields and printable relief geometry.

Its primary purpose is creating physical surfaces for ceramic applications.

Examples include:

- Fractal ceramic tiles.
- Ceramic press molds.
- Texture plates.
- Raised relief surfaces.
- Recessed relief surfaces.
- Decorative architectural tiles.
- Experimental ceramic textures.
- Mathematical and procedural surfaces.
- Other 3D-printable relief objects.

The application should allow a user to load an image, adjust its tonal values, convert it into a physical heightfield, manipulate the resulting terrain, inspect it in a real-time 3D viewport, and export a printable solid.

The primary workflow is:

1. Load an image.
2. Convert it to grayscale.
3. Adjust Levels and Curves.
4. Apply image filters.
5. Convert image intensity into physical height.
6. Adjust terrain parameters.
7. Preview the result in real time.
8. Generate a solid mesh.
9. Export STL or 3MF.

## 1.2 Product philosophy

ClayField should be a focused creative tool.

It should not become:

- A Photoshop replacement.
- A Blender replacement.
- A general-purpose CAD system.
- A complicated procedural node editor.
- A full mold-engineering package.

Prioritize:

- Excellent image-to-heightfield conversion.
- Useful tonal controls.
- Real-time 3D visualization.
- Accurate physical dimensions.
- Reliable printable geometry.
- Simple operation.
- Fast interaction.

Keep the architecture understandable and maintainable.

## 1.3 Primary user

The intended user is someone working with:

- Images.
- Fractals.
- Grayscale textures.
- Heightmaps.
- Mathematical patterns.
- 3D printing.
- Physical relief surfaces.

The application must be useful for ceramic production but should not be restricted to ceramics.

---

# PART 2 — DEVELOPMENT ENVIRONMENT AND TECHNOLOGY

## 2.1 Target hardware

The primary development machine has:

- NVIDIA RTX 5070 Ti.
- 16 GB GPU memory.
- AMD Ryzen 9 9950X.
- Approximately 45 GB system memory.
- Ubuntu Linux.

The application should take advantage of this hardware without requiring it.

It must also work on ordinary Linux systems with supported OpenGL hardware.

## 2.2 Technology stack

Use this stack:

| Component | Technology | Responsibility |
|---|---|---|
| Programming language | Python 3.12+ | Application logic |
| GUI | PySide6 | Desktop interface |
| OpenGL integration | PyOpenGL | Rendering API |
| OpenGL | OpenGL 3.3 Core+ | GPU rendering |
| Shader language | GLSL 330+ | GPU operations |
| Image processing | OpenCV | Image loading and processing |
| Numerical arrays | NumPy | Heightfield calculations |
| Scientific operations | SciPy | Interpolation and smoothing |
| Mesh generation | NumPy | Physical mesh construction |
| Mesh inspection | Trimesh | Validation and export |
| Testing | Pytest | Automated tests |
| Packaging | PyInstaller or equivalent | Linux distribution |

Use Qt's OpenGL integration, preferably QOpenGLWidget, for the viewport.

The application should use OpenGL 3.3 Core as its baseline. Newer OpenGL features may be used when available, but the basic application should not depend on them.

## 2.3 Dependencies

Initial Python dependencies:

```text
PySide6
PyOpenGL
PyOpenGL-accelerate
numpy
opencv-python
scipy
trimesh
pytest
```

Additional dependencies may be introduced when required.

Do not install unnecessary libraries.

Do not introduce CUDA, Taichi, Vulkan, Unity, Unreal, or C++ extensions unless a demonstrated technical requirement justifies them.

GPU processing should initially use OpenGL and GLSL.

## 2.4 Project setup

Use a Python virtual environment.

Development installation should be straightforward:

```bash
mkdir -p ~/dev/clayfield
cd ~/dev/clayfield

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip

pip install \
    PySide6 \
    PyOpenGL \
    PyOpenGL-accelerate \
    numpy \
    opencv-python \
    scipy \
    trimesh \
    pytest
```

Use pyproject.toml as the authoritative dependency and project configuration.

Provide a simple development launch command:

```bash
python main.py
```

---

# PART 3 — APPLICATION INTERFACE

## 3.1 Main window

The interface should use a conventional desktop layout.

Three main sections:

1. Image controls.
2. Central 3D viewport.
3. Terrain controls.

Suggested layout:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ File   Edit   Image   Terrain   View   Export                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ IMAGE PANEL        │             3D VIEWPORT       │ TERRAIN PANEL  │
│                    │                               │                │
│ Load Image         │                               │ Dimensions     │
│                    │                               │                │
│ Grayscale          │                               │ Width          │
│ Invert             │                               │ Depth          │
│                    │                               │                │
│ LEVELS             │                               │ Relief Height  │
│ Black point        │                               │ Minimum Height │
│ Midpoint           │                               │ Base Thickness │
│ White point        │                               │                │
│                    │                               │ Resolution     │
│ CURVES             │                               │                │
│                    │                               │ Mapping        │
│ Brightness         │                               │                │
│ Contrast           │                               │ Smoothing      │
│ Gamma              │                               │ Noise          │
│                    │                               │                │
│ FILTERS            │                               │ Edge Falloff   │
│ Blur               │                               │                │
│ Sharpen            │                               │                │
│ Threshold          │                               │                │
│                    │                               │                │
├────────────────────┴───────────────────────────────┴────────────────┤
│ Histogram / Heightmap Preview / Status                               │
└─────────────────────────────────────────────────────────────────────┘
```

The 3D viewport should receive most of the screen space.

Panels should be resizable.

Use collapsible control groups to avoid clutter.

## 3.2 Menus

Implement:

**File**
- New Project.
- Open Image.
- Open Project.
- Save Project.
- Save Project As.
- Export.
- Exit.

**Edit**
- Undo.
- Redo.
- Reset Current Settings.

**Image**
- Grayscale.
- Invert.
- Levels.
- Curves.
- Filters.

**Terrain**
- Height Mapping.
- Smoothing.
- Noise.
- Edge Falloff.

**View**
- Reset Camera.
- Fit Terrain.
- Top View.
- Front View.
- Side View.
- Isometric View.
- Wireframe.
- Height Coloring.

**Export**
- STL.
- 3MF.
- PNG Heightmap.
- TIFF Heightmap.

## 3.3 Interface behavior

All important parameters should have:

- Slider.
- Numeric input.
- Reset button.
- Tooltip.

The user must be able to enter exact physical dimensions rather than relying exclusively on sliders.

Provide a dark theme.

The interface should remain responsive while processing images or exporting meshes.

---

# PART 4 — APPLICATION ARCHITECTURE

## 4.1 General architecture

Separate the application into five primary systems:

1. User interface.
2. Image processing.
3. Terrain generation.
4. OpenGL rendering.
5. Geometry and export.

These systems should communicate through a central project state and a processing pipeline.

Do not allow each UI panel to maintain its own competing copy of project parameters.

## 4.2 Processing pipeline

The complete pipeline:

```text
SOURCE IMAGE
     |
     v
IMAGE LOADING
     |
     v
COLOR / GRAYSCALE CONVERSION
     |
     v
IMAGE ADJUSTMENTS
     |
     ├── Levels
     ├── Curves
     ├── Brightness
     ├── Contrast
     └── Gamma
     |
     v
IMAGE FILTERS
     |
     ├── Blur
     ├── Sharpen
     └── Threshold
     |
     v
HEIGHT MAPPING
     |
     v
TERRAIN MODIFIERS
     |
     ├── Smoothing
     ├── Noise
     └── Edge Falloff
     |
     v
FINAL HEIGHTFIELD
     |
     ├─────────────────────┐
     |                     |
     v                     v
GPU RENDERING         CPU GEOMETRY
     |                     |
     v                     v
3D PREVIEW            SOLID MESH
                           |
                           v
                       VALIDATION
                           |
                           v
                        EXPORT
```

## 4.3 Central project state

Implement a central ProjectState.

It should contain:

```python
ProjectState:
    source_image
    image_settings
    levels_settings
    curves_settings
    filter_settings
    height_settings
    terrain_settings
    physical_dimensions
    rendering_settings
    export_settings
```

The UI modifies this state.

The processing pipeline consumes it.

The project serializer saves it.

The renderer displays its results.

The exporter generates physical geometry from its authoritative heightfield.

## 4.4 Data representation

Use NumPy arrays for image and heightfield processing.

Primary representations:

```python
source_image
grayscale_image
adjusted_image
normalized_heightfield
physical_heightfield
```

Use float32 for normalized and physical heightfield arrays.

Normalized heights should generally occupy the range 0–1.

Physical heights should be represented in millimeters.

Do not confuse grayscale values with physical heights.

The authoritative CPU physical heightfield must be available for mesh generation and export.

## 4.5 Processing cache

Implement a simple dependency-based processing cache.

Only recalculate stages affected by parameter changes.

Example:

| Changed parameter | Recalculate |
|---|---|
| Brightness | Image adjustments onward |
| Levels | Image adjustments onward |
| Curves | Image adjustments onward |
| Blur | Filters onward |
| Maximum height | Height mapping onward |
| Noise amplitude | Terrain modifiers onward |
| Base thickness | Mesh generation only |
| Camera orbit | Rendering only |

Do not introduce a complicated node editor.

A simple staged processing pipeline is sufficient.

---

# PART 5 — IMAGE PROCESSING

This is a core part of ClayField.

The user should be able to transform ordinary photographs, fractal images, and generated textures into useful relief surfaces.

## 5.1 Image loading

Support:

- PNG.
- JPEG.
- TIFF.
- BMP.

Handle:

- RGB.
- RGBA.
- Grayscale.
- 8-bit images.
- 16-bit images.

Requirements:

- Preserve the original source.
- Preserve 16-bit precision where possible.
- Handle EXIF orientation.
- Handle transparency.
- Display image dimensions.
- Provide fit-to-panel preview.
- Handle invalid images gracefully.

Do not silently convert all input to 8-bit.

## 5.2 Grayscale

Provide luminance-based grayscale conversion.

Do not simply average the three color channels.

For color images, handle sRGB correctly when converting to linear luminance.

The application should also support direct use of grayscale input.

Provide an invert option.

## 5.3 Levels

Implement Photoshop-style Levels.

Parameters:

- Input black point.
- Input midpoint/gamma.
- Input white point.
- Output black point.
- Output white point.

Display a histogram.

Basic transformation:

```python
normalized = (image - black_point) / (
    white_point - black_point
)

normalized = np.clip(normalized, 0.0, 1.0)

adjusted = normalized ** (1.0 / gamma)

adjusted = output_black + adjusted * (
    output_white - output_black
)
```

Validate the black and white point relationship.

Provide reset functionality.

Update the image preview when controls change.

## 5.4 Histogram

Display a histogram of the current image.

Requirements:

- 256 or more histogram bins.
- Input range visibility.
- Output range visibility.
- Clipping indicators where practical.
- Refresh when image processing changes.

The histogram should help identify tonal clipping and poor contrast.

## 5.5 Curves

Implement a simple interactive tone curve.

The editor should provide:

- Square graph.
- Input intensity horizontal axis.
- Output intensity vertical axis.
- Default diagonal line.
- Add control points.
- Move control points.
- Remove control points.
- Reset curve.

Use a lookup table for efficient processing.

Recommended implementation:

1. Store control points.
2. Sort points by input position.
3. Interpolate the curve.
4. Generate a 4096-entry LUT.
5. Apply the LUT using NumPy or a GLSL shader.

Use stable interpolation.

Avoid unexpected overshoot and oscillations.

Do not build a full Photoshop-style curve editor.

## 5.6 Additional image controls

Implement:

- Brightness.
- Contrast.
- Gamma.
- Invert.
- Gaussian blur.
- Sharpen.
- Threshold.
- Crop.
- Resize.

Each operation must have understandable controls and reset functionality.

Preserve the original image.

---

# PART 6 — HEIGHTFIELD GENERATION

This is the central functionality of ClayField.

The application converts image intensity into a physical heightfield.

## 6.1 Mathematical definition

Let:

- I = normalized image intensity.
- f(I) = user-defined height mapping function.
- Hmin = minimum physical height.
- Hmax = maximum physical height.

The height equation is:

```text
height = Hmin + f(I) × (Hmax - Hmin)
```

For linear mapping:

```text
f(I) = I
```

For inverted mapping:

```text
f(I) = 1 - I
```

The application should clearly distinguish:

1. Image intensity.
2. Normalized height.
3. Physical height.

## 6.2 Height controls

Provide:

- Minimum height.
- Maximum height.
- Height offset.
- Height scale.
- Invert.
- Mapping curve.
- Clamp.
- Normalize.

All physical height values must be expressed in millimeters.

## 6.3 Physical dimensions

Provide:

- Width.
- Depth.
- Relief height.
- Base thickness.

Example:

```text
Width:          100 mm
Depth:          100 mm
Relief height:    8 mm
Base thickness:   5 mm
```

Maintain image aspect ratio by default.

Allow the user to unlock width and depth independently.

## 6.4 Height mapping curve

The height-mapping curve must be independent of the image Levels and Curves controls.

This distinction is essential.

Image Curves modify tonal intensity.

Height Mapping determines how intensity becomes physical height.

For example, the user may want:

- Dark regions to remain almost flat.
- Midtones to rise gradually.
- Bright regions to rise sharply.
- Maximum relief to remain 5 mm.

Provide an editable mapping curve.

## 6.5 Heightfield resolution

Support:

- 128 × 128.
- 256 × 256.
- 512 × 512.
- 1024 × 1024.
- 2048 × 2048.
- Original image resolution.

Preview resolution and export resolution must be independent.

Do not unnecessarily render export-resolution geometry in the viewport.

## 6.6 Edge falloff

Implement optional edge falloff.

Purpose:

Transition the terrain toward a flat perimeter.

Controls:

- Falloff width.
- Falloff strength.
- Falloff type.

Initial modes:

- Linear.
- Smoothstep.

The edge falloff should be calculated in a predictable manner and reflected in the final exported geometry.

---

# PART 7 — TERRAIN MODIFIERS

Terrain modifiers are mathematical operations applied to the heightfield.

Keep them simple.

Each modifier should have an enabled/disabled control.

## 7.1 Smoothing

Use Gaussian smoothing.

Controls:

- Radius.
- Strength.

Allow smoothing to be adjusted without permanently changing the original heightfield.

## 7.2 Noise

Implement basic procedural noise.

Controls:

- Amplitude.
- Frequency.
- Seed.

The seed should make results reproducible.

## 7.3 Fractal noise

Allow several noise octaves.

Controls:

- Octaves.
- Persistence.
- Frequency.
- Amplitude.

## 7.4 Displacement

Allow a secondary image or noise field to influence terrain height.

Keep the first implementation simple.

## 7.5 Radial waves

Optional procedural modifier.

Controls:

- Frequency.
- Amplitude.
- Center.
- Phase.

Do not implement an elaborate procedural modeling environment.

---

# PART 8 — GPU ARCHITECTURE AND OPENGL

The GPU should be a major part of the application.

The RTX 5070 Ti has enough capability to support real-time image adjustments and heightfield visualization.

## 8.1 Hybrid GPU/CPU architecture

Use a hybrid system.

```text
                 SOURCE IMAGE
                      |
                      v
                 CPU / OpenCV
                      |
                      v
                 SOURCE TEXTURE
                      |
                      v
               GPU IMAGE PIPELINE
                      |
              ┌───────┼────────┐
              |       |        |
            Levels  Curves   Filters
              |       |        |
              └───────┼────────┘
                      |
                      v
                HEIGHT MAPPING
                      |
                      v
              FLOAT HEIGHT TEXTURE
                      |
              ┌───────┴────────┐
              |                |
              v                v
         GPU RENDERING     CPU READBACK
              |                |
              v                v
          3D PREVIEW      CPU HEIGHTFIELD
                               |
                               v
                         MESH GENERATION
                               |
                               v
                            EXPORT
```

The GPU is responsible for responsive preview processing.

The CPU maintains a reliable reference processing pipeline and the authoritative data needed for mesh generation.

## 8.2 OpenGL implementation

Use:

- OpenGL 3.3 Core.
- GLSL 330 or newer.
- Vertex shaders.
- Fragment shaders.
- Vertex buffer objects.
- Index buffer objects.
- Vertex array objects.
- Texture objects.
- Framebuffer objects.
- Depth testing.

Use floating-point textures for height data.

Recommended height texture:

```text
GL_R32F
```

Use appropriate texture formats for source images.

## 8.3 GPU image processing

Implement image adjustments as shader operations where practical.

Possible shader stages:

- Grayscale.
- Levels.
- Curves LUT.
- Brightness.
- Contrast.
- Gamma.
- Basic filters.
- Height mapping.

Use framebuffer objects to process images.

Use ping-pong textures for sequential operations.

Avoid unnecessary CPU/GPU transfers.

The GPU processing output must agree with the CPU reference implementation within a documented tolerance.

Do not make the GPU the only source of truth.

## 8.4 Real-time terrain displacement

Use a regular grid and a floating-point height texture.

```text
NUMPY HEIGHTFIELD
       |
       v
GPU FLOAT TEXTURE
       |
       v
REGULAR GRID
       |
       v
VERTEX SHADER
       |
       v
HEIGHT SAMPLING
       |
       v
VERTEX DISPLACEMENT
       |
       v
FRAGMENT SHADING
       |
       v
3D VIEWPORT
```

The grid should sample the height texture and displace vertices.

Do not rebuild a massive CPU mesh every time a slider changes.

## 8.5 Preview resolution

Preview grid resolution and height texture resolution should be independent.

Example:

```text
Height texture: 2048 × 2048
Preview grid:    512 × 512
Export mesh:    2048 × 2048
```

This permits high-resolution height information without forcing the viewport to render every sample.

## 8.6 Normal calculation

Calculate appropriate terrain normals.

Options:

- Derive normals from neighboring height samples.
- Calculate normals in the shader using height gradients.

Avoid visible lighting artifacts.

Ensure the shader and mesh generator use consistent surface orientation.

## 8.7 Viewport controls

Implement:

- Orbit.
- Pan.
- Zoom.
- Reset camera.
- Fit terrain.
- Top view.
- Front view.
- Side view.
- Isometric view.
- Perspective projection.
- Orthographic projection.

Mouse:

- Left drag: orbit.
- Middle drag: pan.
- Scroll: zoom.

## 8.8 Display modes

Implement three useful visualization modes:

**Lit Surface**
- Normal 3D shading.
- Adjustable lighting.
- Surface color.

**Height Coloring**
- Color based on physical height.
- Adjustable color range.

**Wireframe**
- Show grid density.
- Inspect surface topology.

Also provide grid visibility.

## 8.9 OpenGL resource management

Implement proper GPU resource handling.

Requirements:

- Reuse buffers.
- Update textures only when necessary.
- Avoid unnecessary shader recompilation.
- Release replaced textures.
- Handle context destruction correctly.
- Keep OpenGL calls on the GUI/render thread.
- Handle initialization errors.
- Display GPU and OpenGL information.

---

# PART 9 — PHYSICAL COORDINATES AND GEOMETRY

## 9.1 Coordinate system

Define one coordinate convention throughout the application.

Use:

| Axis | Meaning |
|---|---|
| X | Width |
| Y | Height |
| Z | Depth |

All geometry uses millimeters.

Center the terrain horizontally around:

```text
X = 0
Z = 0
```

The base extends below the terrain.

Example:

```text
Width:          100 mm
Depth:          100 mm
Base thickness:   5 mm
Relief height:    8 mm
```

Expected model bounds:

```text
X: -50 to +50 mm
Z: -50 to +50 mm
Y: -5 to +8 mm
```

Document this convention.

Use it consistently in rendering, mesh generation, and export.

## 9.2 Pixel-to-geometry conversion

The application must define how image rows and columns map to physical X and Z positions.

Be explicit about image row orientation.

Test for vertical and horizontal inversion.

The viewport and exported mesh must use the same orientation.

## 9.3 Positive and negative relief

Implement two geometry modes.

**Positive relief**

Image intensity produces raised terrain.

**Negative relief**

Image intensity produces recessed terrain.

Both modes must produce closed printable solids.

Do not create two unrelated mesh-generation systems.

Use the same underlying heightfield with a clearly defined transformation.

## 9.4 Base geometry

Initial priority:

Rectangular base.

Controls:

- Width.
- Depth.
- Base thickness.
- Border width.
- Relief height.

Later:

Circular base.

The base should be integrated with the relief into one closed solid.

---

# PART 10 — MESH GENERATION AND VALIDATION

## 10.1 Mesh generation

The CPU mesh generator converts the authoritative physical heightfield into a solid.

Generate:

- Top surface.
- Bottom surface.
- Four side walls.
- Closed perimeter.

Use consistent triangle winding.

Generate correct normals.

Avoid open boundaries.

## 10.2 Mesh resolution

Export resolution must be independent of preview resolution.

Support high-resolution exports where practical.

A 4096 × 4096 heightfield represents over 16 million top-surface samples.

This can produce a very large mesh.

Before generating large meshes, estimate:

- Vertex count.
- Triangle count.
- Memory requirements.
- Approximate export size.

Display warnings for excessive geometry.

Do not silently exhaust system memory.

## 10.3 Mesh validation

Use Trimesh for validation.

Check:

- Watertightness.
- Winding consistency.
- Positive volume.
- Degenerate triangles.
- Non-finite coordinates.
- Bounding dimensions.
- Mesh validity.

Validate the final exported mesh.

Report errors clearly.

Do not silently export invalid geometry.

## 10.4 Geometry accuracy

The exported model must match the physical dimensions displayed in the application.

Do not apply hidden scaling.

Do not apply arbitrary unit conversions.

Use millimeters throughout the geometry system.

---

# PART 11 — EXPORT

## 11.1 Initial formats

Implement:

- STL.
- 3MF.
- PNG heightmap.
- TIFF heightmap.

Implement STL first.

Implement 3MF after solid mesh generation and STL validation are reliable.

Use a tested 3MF-capable library or exporter, such as lib3mf integration where appropriate. Do not assume that every Trimesh installation supports every 3MF export operation.

## 11.2 Export dialog

Provide:

- Filename.
- Output format.
- Width.
- Depth.
- Relief height.
- Base thickness.
- Export resolution.
- Positive/negative mode.

Show the expected physical dimensions.

Show a mesh validation summary.

## 11.3 Export verification

Test exported files in an independent 3D-printing slicer.

Verify:

- Dimensions.
- Orientation.
- Watertightness.
- Positive volume.
- Surface detail.
- No unexpected scaling.

The export pipeline must be tested independently of the viewport.

---

# PART 12 — PROJECT FILES AND PERSISTENCE

## 12.1 Native project format

Use:

```text
.clayfield
```

Implement the format as a ZIP archive.

Example:

```text
project.clayfield
    |
    ├── project.json
    ├── source_image.png
    └── preview.png
```

Include the original source image so projects remain portable.

## 12.2 Saved parameters

Store:

- Project version.
- Source image information.
- Image adjustments.
- Levels.
- Curves.
- Filters.
- Height mapping.
- Terrain modifiers.
- Physical dimensions.
- Rendering preferences.
- Export settings.

Do not store unnecessary intermediate GPU textures.

Intermediate results should be regenerated when the project opens.

## 12.3 Project functionality

Implement:

- New.
- Open.
- Save.
- Save As.
- Dirty project indicator.
- Recovery/autosave.
- Missing image handling.
- Version compatibility checks.

Save and load must reproduce the same final heightfield.

---

# PART 13 — UNDO, REDO AND APPLICATION STATE

Implement basic undo and redo.

Track meaningful user operations:

- Image adjustments.
- Curves.
- Height mapping.
- Terrain modifiers.
- Physical dimensions.

Use parameter-state snapshots or command history.

Do not store a complete copy of a large image every time a slider moves.

Group continuous slider changes into one undo operation.

Provide reset functionality for individual sections.

---

# PART 14 — RESPONSIVENESS AND PERFORMANCE

## 14.1 Performance goals

Target hardware includes the RTX 5070 Ti 16 GB.

Expected working resolutions:

| Resolution | Intended use |
|---|---|
| 256 × 256 | Fast preview |
| 512 × 512 | Normal preview |
| 1024 × 1024 | High-quality preview |
| 2048 × 2048 | High-quality output |
| 4096 × 4096 | Advanced output |

These are targets, not guaranteed performance specifications.

## 14.2 UI responsiveness

The GUI must not freeze during expensive operations.

Use background workers for:

- Large CPU image-processing operations.
- Mesh generation.
- Export.
- Expensive validation.

Keep OpenGL calls on the rendering thread.

Provide progress indicators.

Allow cancellation where practical.

## 14.3 Performance optimization

Prioritize:

- Avoiding unnecessary array copies.
- Caching intermediate results.
- Reusing OpenGL buffers.
- Updating textures selectively.
- Debouncing slider operations.
- Independent preview/export resolution.
- Efficient NumPy operations.

Do not optimize prematurely.

Profile actual bottlenecks before introducing more complicated technologies.

---

# PART 15 — ADDITIONAL USEFUL FEATURES

These features are appropriate for the application but should not delay the core workflow.

## 15.1 Heightmap preview

Display the current heightfield as a 2D grayscale image.

This lets the user inspect the actual height data independently of the 3D viewport.

## 15.2 Before/after comparison

Allow comparison between:

- Original image.
- Adjusted image.
- Final heightmap.

## 15.3 Height range display

Show:

- Minimum height.
- Maximum height.
- Height range.
- Physical dimensions.

## 15.4 Cross-section preview

Add a cross-section tool.

The user should be able to move a line across the terrain and inspect its height profile.

Display:

- Physical distance.
- Minimum height.
- Maximum height.
- Profile shape.

This is particularly useful for evaluating ceramic relief depth.

It is not essential for the first release.

## 15.5 Presets

Allow users to save and load adjustment presets.

Presets should store parameters, not full project files.

---

# PART 16 — FUTURE FEATURES

Do not implement these during the initial development.

They are possible future extensions.

## Procedural generators

- Mandelbrot.
- Julia sets.
- Voronoi.
- Reaction-diffusion.
- Mathematical wave patterns.
- Additional fractal generators.

## Ceramic tools

- Clay shrinkage compensation.
- Draft angle analysis.
- Mold release considerations.
- Tile repetition.
- Tile arrays.
- Firing-related compensation.

## Advanced image tools

- Multiple image layers.
- Image masks.
- Additional filters.
- Local contrast.
- Frequency-based adjustments.

## Advanced terrain tools

- Sculpting brushes.
- Local displacement.
- Multiple heightfield layers.
- More procedural modifiers.

The architecture should permit future additions without requiring them now.

---

# PART 17 — COMPLETE DIRECTORY STRUCTURE

Use the following project structure.

```text
clayfield/
│
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── .gitignore
├── main.py
│
├── assets/
│   ├── icons/
│   ├── themes/
│   └── examples/
│
├── shaders/
│   ├── image_process.vert
│   ├── image_process.frag
│   ├── terrain.vert
│   ├── terrain.frag
│   └── grid.vert
│
├── src/
│   └── clayfield/
│       │
│       ├── __init__.py
│       │
│       ├── app/
│       │   ├── application.py
│       │   ├── project.py
│       │   ├── project_state.py
│       │   ├── project_io.py
│       │   └── settings.py
│       │
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── main_window.py
│       │   ├── viewport.py
│       │   ├── image_panel.py
│       │   ├── terrain_panel.py
│       │   ├── export_panel.py
│       │   ├── histogram.py
│       │   ├── curve_editor.py
│       │   └── widgets/
│       │       ├── parameter_slider.py
│       │       └── collapsible_section.py
│       │
│       ├── image/
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   ├── grayscale.py
│       │   ├── levels.py
│       │   ├── curves.py
│       │   ├── filters.py
│       │   └── pipeline.py
│       │
│       ├── terrain/
│       │   ├── __init__.py
│       │   ├── heightfield.py
│       │   ├── mapping.py
│       │   ├── modifiers.py
│       │   ├── noise.py
│       │   └── edge_falloff.py
│       │
│       ├── rendering/
│       │   ├── __init__.py
│       │   ├── renderer.py
│       │   ├── camera.py
│       │   ├── textures.py
│       │   ├── shaders.py
│       │   ├── gpu_pipeline.py
│       │   └── mesh_grid.py
│       │
│       ├── geometry/
│       │   ├── __init__.py
│       │   ├── mesh_generator.py
│       │   ├── base_geometry.py
│       │   ├── normals.py
│       │   └── validation.py
│       │
│       ├── export/
│       │   ├── __init__.py
│       │   ├── stl.py
│       │   ├── three_mf.py
│       │   └── heightmap.py
│       │
│       └── core/
│           ├── __init__.py
│           ├── history.py
│           ├── worker.py
│           ├── cache.py
│           ├── signals.py
│           └── constants.py
│
├── tests/
│   ├── test_image_loading.py
│   ├── test_grayscale.py
│   ├── test_levels.py
│   ├── test_curves.py
│   ├── test_heightfield.py
│   ├── test_mapping.py
│   ├── test_pipeline.py
│   ├── test_mesh.py
│   ├── test_validation.py
│   ├── test_export.py
│   └── test_project.py
│
└── docs/
    ├── architecture.md
    ├── development.md
    └── user_guide.md
```

Do not create empty modules for every future feature.

Create files as functionality is implemented.

The structure may be simplified if the implementation demonstrates a clear reason, but avoid putting the entire application into one or two giant Python files.

---

# PART 18 — TESTING AND VALIDATION

Use Pytest.

Test numerical processing independently of the GUI.

## 18.1 Image processing tests

Test:

- Grayscale conversion.
- RGB and RGBA handling.
- 8-bit and 16-bit images.
- Levels.
- Gamma.
- Curves LUT.
- Brightness.
- Contrast.
- Inversion.
- Filters.
- Invalid input handling.

## 18.2 Heightfield tests

Test:

- Correct dimensions.
- Correct physical height range.
- Minimum and maximum height.
- Inversion.
- Mapping curves.
- Edge falloff.
- Smoothing.
- Noise reproducibility.
- Aspect ratio.
- NaN and infinity rejection.

## 18.3 Pipeline tests

Test:

- Correct processing order.
- Cache invalidation.
- Unaffected stages remaining cached.
- Recalculation after parameter changes.
- CPU/GPU agreement where automated GPU testing is available.

## 18.4 Mesh tests

Test:

- Watertightness.
- Positive volume.
- Correct dimensions.
- Correct orientation.
- Consistent face winding.
- Degenerate triangles.
- Non-finite coordinates.
- Positive relief.
- Negative relief.
- Base thickness.

## 18.5 Project tests

Test:

- Save.
- Load.
- Parameter preservation.
- Source image preservation.
- Invalid project handling.
- Version compatibility.

## 18.6 Export tests

Test:

- STL generation.
- STL reopening.
- 3MF generation.
- 3MF reopening.
- Physical dimensions.
- Watertightness.
- Slicer compatibility.

---

# PART 19 — DEVELOPMENT ROADMAP

Development must proceed through milestones.

Do not attempt to build the entire application in one pass.

Each milestone must produce a working, testable application.

## MILESTONE 1 — Desktop Application Foundation

Goal: A working Linux desktop application with an OpenGL viewport.

Implement:

- Project structure.
- Python virtual environment.
- PySide6 application.
- Main window.
- Menu bar.
- Three-panel layout.
- OpenGL viewport.
- OpenGL 3.3 Core initialization.
- Basic 3D grid or test object.
- Camera orbit.
- Camera zoom.
- Basic error handling.

Acceptance criteria:

- Application launches on Ubuntu.
- Window resizes correctly.
- Panels work.
- OpenGL context initializes.
- Test geometry renders.
- Camera works.
- No major startup errors.

Deliverable:

A functioning desktop application shell.

Do not implement image processing yet.

## MILESTONE 2 — Image Loading and Display

Goal: Load and display source images.

Implement:

- Image file dialog.
- PNG.
- JPEG.
- TIFF.
- BMP.
- Image preview.
- Grayscale conversion.
- Invert.
- Image dimensions.
- Original image storage.

Acceptance criteria:

- Different formats load.
- Color images display.
- Grayscale works.
- Original image remains preserved.
- Invalid images produce useful errors.

Deliverable:

A working image-processing foundation.

## MILESTONE 3 — Image Adjustments

Goal: Provide meaningful tonal control.

Implement:

- Histogram.
- Levels.
- Gamma.
- Brightness.
- Contrast.
- Curves editor.
- LUT generation.
- Gaussian blur.
- Sharpen.
- Threshold.
- Reset controls.

Acceptance criteria:

- Image updates when controls change.
- Histogram updates.
- Curves work.
- Original image is preserved.
- The interface remains responsive.

Deliverable:

A functional image preparation application.

## MILESTONE 4 — First Real-Time Heightfield

Goal: Turn an image into a visible 3D surface.

Implement:

- Heightfield generation.
- Physical dimensions.
- Maximum relief.
- Minimum height.
- Height offset.
- Inversion.
- Height mapping.
- GPU height texture.
- Regular grid.
- Vertex displacement.
- Fragment shading.
- Basic camera and lighting.

Acceptance criteria:

- Image becomes a 3D surface.
- Levels updates terrain.
- Curves updates terrain.
- Relief height updates terrain.
- Camera remains responsive.
- Physical dimensions are reflected correctly.

This is the first major functional milestone.

Do not proceed to elaborate features until this works reliably.

## MILESTONE 5 — GPU Image Processing and Pipeline

Goal: Make image-to-terrain updates efficient.

Implement:

- GPU image textures.
- Framebuffer processing.
- Levels shader.
- Curves shader.
- Height mapping shader.
- Floating-point height texture.
- CPU reference processing.
- Processing cache.
- Dependency invalidation.
- GPU/CPU consistency tests.

Acceptance criteria:

- Image adjustments update the viewport.
- No unnecessary CPU/GPU transfers.
- CPU reference produces matching results within documented tolerance.
- Changing camera position does not trigger processing.
- Changing base thickness does not trigger image processing.
- GPU resources are released correctly.

Deliverable:

A reliable accelerated processing pipeline.

## MILESTONE 6 — Terrain Controls

Goal: Make the terrain useful for actual physical design.

Implement:

- Minimum height.
- Maximum height.
- Height offset.
- Mapping curve.
- Smoothing.
- Edge falloff.
- Noise.
- Fractal noise.
- Preview resolution.
- Export resolution.

Acceptance criteria:

- Parameters update the terrain.
- Modifiers are independently enabled.
- Results are reproducible.
- Reset controls work.
- Physical dimensions remain accurate.

## MILESTONE 7 — Solid Mesh Generation

Goal: Generate printable solid geometry.

Implement:

- Rectangular base.
- Positive relief.
- Negative relief.
- Top surface.
- Bottom surface.
- Side walls.
- Mesh normals.
- Consistent winding.
- Watertight validation.
- Geometry dimension checks.

Acceptance criteria:

- Generated mesh is closed.
- Dimensions match the UI.
- Positive and negative relief work.
- Base thickness is correct.
- Mesh validation reports errors.
- Mesh can be independently inspected.

## MILESTONE 8 — STL and 3MF Export

Goal: Produce usable 3D-printable files.

Implement:

- STL export.
- 3MF export.
- PNG heightmap export.
- TIFF heightmap export.
- Export resolution.
- Progress indicators.
- Mesh validation.
- Export warnings.

Acceptance criteria:

- STL opens in a slicer.
- 3MF opens in a compatible application.
- Physical dimensions are correct.
- Exported geometry is watertight.
- Export matches the displayed heightfield.
- Large exports produce useful warnings.

## MILESTONE 9 — Project Save and Load

Goal: Preserve complete projects.

Implement:

- Native .clayfield format.
- Save.
- Save As.
- Open.
- Embedded source image.
- Processing parameters.
- Project versioning.
- Recovery/autosave.
- Dirty project indicator.

Acceptance criteria:

- Save a project.
- Close the application.
- Reopen it.
- Reproduce the same image adjustments.
- Reproduce the same physical heightfield.

## MILESTONE 10 — Application Refinement

Goal: Make ClayField reliable and pleasant to use.

Implement:

- Undo.
- Redo.
- Better error handling.
- Performance improvements.
- Viewport polish.
- Camera presets.
- Height coloring.
- Wireframe.
- Heightmap preview.
- Before/after image comparison.
- Documentation.
- Linux packaging.

Acceptance criteria:

- Normal use does not cause major crashes.
- Large images are handled sensibly.
- Export errors are reported.
- Projects remain portable.
- Installation is straightforward.

## MILESTONE 11 — Advanced Tools

Only after the previous milestones are complete:

- Cross-section preview.
- Circular base.
- Beveled borders.
- Tile repetition.
- Presets.
- Additional procedural generators.
- Mandelbrot.
- Julia sets.
- Voronoi patterns.
- Ceramic shrinkage compensation.

These are future extensions, not prerequisites for the first release.

---

# PART 20 — PERFORMANCE AND QUALITY TARGETS

The application should be designed to work efficiently with modern GPUs.

Target:

- Smooth interaction at 512 × 512.
- Smooth interaction at 1024 × 1024.
- Responsive image adjustment.
- Responsive camera movement.
- Independent high-resolution export.
- No unnecessary geometry reconstruction.

Do not promise a fixed frame rate before profiling.

Measure:

- Image processing time.
- GPU texture update time.
- Viewport frame rate.
- Mesh generation time.
- Export time.
- Peak memory consumption.

Use profiling results to guide optimization.

---

# PART 21 — DEVELOPMENT RULES FOR THE CODING LLM

These rules must be followed throughout development.

## Architecture

1. Python is the primary language.
2. PySide6 is the desktop GUI.
3. OpenGL is the real-time rendering system.
4. GLSL is used for GPU processing.
5. NumPy provides CPU reference calculations.
6. Image processing is separate from rendering.
7. Mesh generation is separate from rendering.
8. Physical dimensions use millimeters.
9. One authoritative physical heightfield is maintained.
10. The application uses a central project state.

## Code quality

1. Use type hints.
2. Use descriptive variable names.
3. Document important functions.
4. Keep functions focused.
5. Avoid unnecessarily large source files.
6. Avoid excessive class hierarchies.
7. Handle exceptions.
8. Do not silently ignore errors.
9. Write tests for numerical operations.
10. Keep dependencies minimal.

## User interface

1. Important values must be numerically editable.
2. Sliders must update the viewport.
3. Controls must have clear labels.
4. Reset buttons should be available.
5. The viewport should remain central.
6. Expensive operations must not freeze the interface.
7. Provide progress information.

## GPU

1. Use OpenGL 3.3 Core or newer.
2. Use floating-point height textures.
3. Avoid unnecessary CPU/GPU transfers.
4. Keep OpenGL calls on the rendering thread.
5. Reuse GPU resources.
6. Handle context destruction safely.
7. Test GPU/CPU consistency.

## Geometry

1. All physical dimensions are in millimeters.
2. Use a documented coordinate system.
3. Generate closed solids.
4. Validate final meshes.
5. Do not silently scale geometry.
6. Report invalid geometry.
7. Estimate memory before large mesh generation.

## Development discipline

1. Implement one milestone at a time.
2. Keep the application runnable.
3. Test each milestone.
4. Do not implement future features prematurely.
5. Update documentation.
6. Report modified files.
7. Report known bugs.
8. Never claim untested functionality works.
9. Do not replace working architecture without a clear reason.
10. Do not introduce additional frameworks without justification.

---

# PART 22 — CODING MODEL WORKFLOW

The coding model should work as an engineering collaborator.

At the start of development:

1. Inspect the existing repository.
2. Inspect the installed Python version.
3. Inspect available OpenGL support.
4. Inspect GPU availability.
5. Inspect installed dependencies.
6. Create or verify the virtual environment.
7. Create the initial project structure.
8. Implement Milestone 1.

Do not overwrite an existing working project without inspecting it first.

## After each milestone

The coding model must provide:

1. Summary of implementation.
2. Files created.
3. Files modified.
4. Dependencies added.
5. Tests performed.
6. Test results.
7. Known limitations.
8. Performance observations.
9. Remaining work.
10. Recommended next milestone.

The model should not skip milestones merely because it can generate code for later functionality.

## When something fails

The model must:

1. Identify the actual error.
2. Explain the cause.
3. Fix the problem.
4. Run the relevant tests again.
5. Verify the application still launches.
6. Document any remaining limitations.

Do not hide errors with broad exception handling.

Do not substitute mock functionality for completed functionality.

---

# PART 23 — FIRST ASSIGNMENT

Begin development with Milestone 1 only.

The first assignment is to create a working Linux desktop application with an OpenGL viewport.

### Required tasks

1. Inspect the Ubuntu development environment.
2. Create the ClayField repository structure.
3. Create the virtual environment.
4. Install initial dependencies.
5. Create main.py.
6. Create the PySide6 application.
7. Create the main window.
8. Implement the three-panel layout.
9. Initialize an OpenGL 3.3 Core context.
10. Create a simple 3D grid or test object.
11. Implement orbit and zoom.
12. Implement camera reset.
13. Display basic GPU/OpenGL information.
14. Test application startup.

### First deliverable

A running application with:

- Working main window.
- Image panel placeholder.
- Terrain panel placeholder.
- Functional OpenGL viewport.
- Camera controls.
- Basic 3D rendering.

Do not implement image processing yet.

Do not implement heightfields yet.

Do not implement mesh export yet.

### Completion report

When finished, provide:

- Files created.
- Dependencies installed.
- Launch instructions.
- Tests performed.
- OpenGL version detected.
- GPU information detected.
- Remaining problems.
- Confirmation that Milestone 1 is complete.

Wait for review before beginning Milestone 2.

---

# PART 24 — DEFINITION OF DONE

ClayField's first complete release is successful when a user can:

1. Launch the application on Linux.
2. Load a color or grayscale image.
3. Adjust grayscale conversion.
4. Adjust Levels.
5. Adjust Curves.
6. Apply image filters.
7. Generate a heightfield.
8. Adjust minimum and maximum physical height.
9. Set width and depth in millimeters.
10. Inspect the terrain in a real-time OpenGL viewport.
11. Change the terrain interactively.
12. Generate a solid positive relief.
13. Generate a solid negative relief.
14. Set base thickness.
15. Generate a watertight mesh.
16. Export STL.
17. Export 3MF.
18. Export a heightmap.
19. Save a native project.
20. Reopen the project and reproduce the same result.

The central objective is a reliable image-to-physical-relief workflow.

Build that exceptionally well before expanding the application.

---

# FINAL DEVELOPMENT PRINCIPLE

ClayField should be a relatively small Python application with a capable GPU rendering system.

Do not confuse a large feature list with a good application.

The most important result is:

IMAGE → IMAGE ADJUSTMENTS → HEIGHTFIELD → REAL-TIME 3D → PRINTABLE SOLID

Every architectural decision should support that workflow.

Build it in stages, test it at every stage, and keep the software understandable.
