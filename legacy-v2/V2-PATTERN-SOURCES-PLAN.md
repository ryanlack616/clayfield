# ClayField V2 Pattern Source Expansion

This document defines the next procedural-source expansion after the current
noise, wave, Mandelbrot, composition, mask, and fabrication pipeline work.

Current status: Batch P1 core sources, P2 geometric/spectral sources, P3
reaction/growth/branching sources, and P4 flow/contour/erosion/tiling core
sources are implemented in the native generator and UI source layers and
covered by bounded-output tests. SDF Boolean operations are now implemented;
the remaining work is richer streamline behavior and production calibration.

Pattern sources remain native deterministic Python/NumPy components. They do not
require external services, neural networks, or GPU execution. External image
tools may produce PNG/TIFF heightmaps and masks for normal file import.

The source contract remains:

```text
shape + parameters + seed + cancellation callback
→ normalized float32 field
→ source metadata and algorithm version
```

Every pattern must work with the existing processing, composition, physical
mapping, fabrication analysis, project persistence, and export paths.

---

## Pattern Design Rules

- Keep every generator deterministic.
- Use normalized domain coordinates rather than unexplained pixel units.
- Support independent preview and export resolutions.
- Expose tileability when the pattern can guarantee it.
- Preserve a fixed-range mode where amplitude has physical meaning.
- Add cancellation checkpoints to long loops.
- Reject or warn about features below the resolved physical sample width.
- Keep generator controls explicit rather than creating a general node editor.
- Store source parameters and algorithm versions in project files.
- Test every pattern through normalized field, physical mapping, mesh, and export.

## Batch P1: Cellular and Warped Terrain

Status: `[~]` Native core implemented; UI and pattern-specific fabrication
controls remain.

### P1.1 Voronoi/Worley fields

Modes:

- Nearest-cell distance.
- Distance to cell boundary.
- Cell ID variation.
- Edge-only crack field.
- Inverted cell field.

Controls:

- Seed.
- Cell density.
- Jitter.
- Edge width.
- Edge softness.
- Contrast.
- Invert.
- Tileable mode.

Uses:

- Crackle ceramics.
- Stone and reptile textures.
- Cellular relief tiles.
- Honeycomb-like surfaces.
- Biological partition patterns.

Fabrication checks:

- Minimum crack width.
- Minimum cell ridge width.
- Disconnected-cell warning.
- High-frequency detail warning.

### P1.2 Ridged multifractal noise

Build on the existing noise generator:

```text
ridge = 1 - abs(noise)
ridge = ridge * ridge
```

Controls:

- Seed.
- Base frequency.
- Octaves.
- Persistence.
- Lacunarity.
- Ridge sharpness.
- Amplitude.
- Normalization.

Uses:

- Mountain relief.
- Geological surfaces.
- Sharp sculptural ridges.
- Eroded ceramic textures.

### P1.3 Domain-warped noise

Use one or more noise fields to displace the sample coordinates of another
field:

```text
x' = x + warp_strength * warp_x(x, y)
y' = y + warp_strength * warp_y(x, y)
field = source(x', y')
```

Controls:

- Source seed.
- Warp seed.
- Source frequency.
- Warp frequency.
- Warp strength.
- Warp octaves.
- Persistence.
- Lacunarity.
- Tileability.

Uses:

- Marble and wood-like flow.
- Organic movement.
- Smoke-like relief.
- Less repetitive terrain.

### P1 gate

- All three patterns are deterministic and bounded.
- All three support physical export.
- Cellular and warped detail warnings are visible.
- Existing generator and project tests remain green.

---

## Batch P2: Geometric and Spectral Sources

Status: `[~]` Chladni, spectral, and SDF core sources are implemented; richer
Boolean geometry and dedicated controls remain.

### P2.1 Signed-distance geometric fields

Primitive shapes:

- Circle.
- Ring.
- Rectangle.
- Rounded rectangle.
- Triangle.
- Polygon.
- Star.
- Superformula shape.
- Arc.
- Line.
- Spiral.

Operations:

- Union.
- Difference.
- Intersection.
- Smooth union.
- Radial repetition.
- Grid repetition.

Controls:

- Shape dimensions.
- Rotation.
- Repeat count.
- Spacing.
- Edge softness.
- Bevel width.
- Smooth-union radius.
- Height or mask mode.

Uses:

- Logos.
- Medallions.
- Geometric reliefs.
- Decorative borders.
- Architectural panels.

The first implementation should support one primitive plus repetition. Full SDF
Boolean composition can follow after the primitive contract is stable.

### P2.2 Chladni and standing-wave fields

Start with separable rectangular modes and add radial/Bessel modes later.

Controls:

- Mode X.
- Mode Y.
- Frequency.
- Phase.
- Symmetry.
- Threshold.
- Line width.
- Radial versus rectangular mode.

Uses:

- Symmetric ceramic panels.
- Nodal-line reliefs.
- Scientific/artistic surfaces.

### P2.3 Fourier and spectral fields

Modes:

- Harmonic sum.
- Directional spectrum.
- Band-limited noise.
- Anisotropic grain.
- Radial frequency bands.

Controls:

- Frequency range.
- Number of components.
- Amplitude falloff.
- Direction.
- Anisotropy.
- Phase randomness.

### P2 gate

- Primitive geometry has exact physical dimensions.
- Repeated geometric patterns are tileable when requested.
- Nodal and spectral patterns pass minimum-feature warnings.
- Pattern parameters survive project round-trip.

---

## Batch P3: Organic Growth and Branching

Status: `[~]` Reaction-diffusion, phyllotaxis, cellular automata, L-system, and
crack-growth core sources are implemented; dedicated controls remain.

### P3.1 Reaction-diffusion

Initial system: Gray-Scott reaction-diffusion.

Controls:

- Feed rate.
- Kill rate.
- Diffusion rates.
- Iteration count.
- Initial seed pattern.
- Symmetry.
- Threshold.
- Blur.

Uses:

- Coral.
- Lichen.
- Skin-like patterns.
- Fungal surfaces.
- Cellular ceramic ornament.

Requirements:

- Bounded workload.
- Cancellation between iteration blocks.
- Tiny-component warnings.
- Minimum-width conditioning.

### P3.2 L-system branching

Represent the output as a rasterized distance field, not a separate mesh path.

Controls:

- Seed.
- Iterations.
- Branch angle.
- Branch length.
- Length reduction.
- Thickness reduction.
- Randomness.
- Growth mask.

Uses:

- Trees.
- Veins.
- Rivers.
- Roots.
- Lightning.
- Leaf skeletons.

### P3.3 Logarithmic spirals and phyllotaxis

Controls:

- Golden-angle or custom angle.
- Arm count.
- Radial growth.
- Turn count.
- Seed spacing.
- Thickness.
- Rotation.
- Radial falloff.

Uses:

- Shells.
- Rosettes.
- Sunflower patterns.
- Pinecone surfaces.
- Radial ceramic ornament.

### P3 gate

- Organic sources remain bounded and cancellable.
- Branches and growth fields have minimum-width controls.
- Disconnected components and tiny islands are reported.
- Representative patterns export as valid solids.

---

## Batch P4: Flow, Contours, and Simulation

Status: `[~]` Flow, erosion-style, and contour core functions are implemented;
streamline controls, crack growth, and production calibration remain.

### P4.1 Flow-field streamlines

Vector fields:

- Curl noise.
- Vortex fields.
- Radial flow.
- Attraction/repulsion points.
- Potential fields.

Controls:

- Seed.
- Flow strength.
- Streamline count.
- Step length.
- Line thickness.
- Vortex centers.
- Decay.
- Mask.

Uses:

- Wind lines.
- Fluid ornament.
- Marble flow.
- Fiber and hair patterns.

### P4.2 Topographic contour modifier

Modes:

- Equal-height contours.
- Variable contour spacing.
- Thick contour lines.
- Filled contour bands.
- Nested contour relief.

Controls:

- Band count.
- Band width.
- Smoothing.
- Contrast.
- Bevel.
- Height modulation.

This should be implemented as a deterministic modifier usable with every scalar
source, not only as a standalone generator.

### P4.3 Hydraulic erosion

Controls:

- Rain amount.
- Droplet count.
- Iterations.
- Erosion strength.
- Sediment capacity.
- Evaporation.
- Seed.

This is computationally expensive and should remain post-V2 unless terrain
realism becomes a primary user requirement.

### P4 gate

- Flow and contour sources remain reproducible.
- Simulation workloads have strict limits and cancellation.
- Export warnings identify small channels and steep features.

---

## Batch P5: Deferred Pattern Families

These are valuable but should not block the first pattern expansion:

- Julia sets.
- Penrose and aperiodic tiling.
- Truchet tiles.
- Cellular automata.
- Perlin-worm cracks.
- Crack propagation.
- Reaction-diffusion variants.
- Voronoi multi-layer materials.

## Pattern Acceptance Checklist

Every new pattern must include:

- [ ] Parameter dataclass and validation.
- [ ] Source descriptor registration.
- [ ] Algorithm version.
- [ ] Normalized float32 output.
- [ ] Seed determinism test.
- [ ] Resolution test.
- [ ] Bounds and finite-value test.
- [ ] Cancellation test for long work.
- [ ] Tileability test when supported.
- [ ] Physical mapping test.
- [ ] Mesh/export test.
- [ ] Fabrication warning test.
- [ ] Project save/load test.
- [ ] UI controls or an explicit post-V2 designation.

## Recommended Build Order

```text
Voronoi/Worley
→ ridged noise
→ domain-warped noise
→ SDF primitives and repetition
→ Chladni modes
→ reaction-diffusion
→ L-system branching
→ spirals/phyllotaxis
→ flow fields
→ contour modifier
→ erosion simulation
```
