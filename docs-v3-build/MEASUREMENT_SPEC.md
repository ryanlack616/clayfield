# Clayfield — Measurement Specification

**Status:** proposed. This is the measurement layer the v3 package leaves open. Adopt it as the authoritative reference for the geometry/mask contract and the SURFACE workspace, or amend it before Phase 3 starts.

**Phase numbering:** follows `IMPLEMENTATION_ROADMAP.md`. `TASK_LIST.md` uses the same numbering.

**Applies to:** the desktop app's heightfield representation. Not the web track.

---

## 0. What this document decides

The v3 package specifies the SURFACE and CLEANUP workspaces but leaves the measurement layer to the implementer. `GUI_LAYOUT.md` §8 names eight analysis methods and requires "a documented mathematical definition"; `TASK_LIST.md` makes that definition a checkbox. This document is the definition. It decides:

1. The metric behind each of the eight analysis methods — formula, units, parameters, validity limits, and what it does *not* detect.
2. What a mask weight means in physical units, and how each mask operation behaves.
3. How the mask is composited in the viewport.
4. A calibrated synthetic fixture that makes each acceptance gate testable.

It does not decide GUI layout, the rendering pipeline, or the export format. Those are already specified and this document does not contradict them.

**One rule governs everything below:** a metric that cannot be computed validly reports *not run* and produces no mask. It does not return zeros, a normalized guess, or a "best effort" heatmap. The v3 spec's "do not show placeholder or fabricated values" applies to the measurement layer as strictly as to the status bar.

---

## 1. Coordinate and sampling contract

### 1.1 The grid

These are the conventions the existing code already uses. The measurement layer must not introduce a second one.

- The heightfield is `heightfield[row, column]`, `float32`, height in **millimetres above the base plane**.
- `row` increases with `+z`; `column` increases with `+x`.
- `x = linspace(-width_mm/2, +width_mm/2, columns)`; `z = linspace(-depth_mm/2, +depth_mm/2, rows)` — the same construction as `src/clayfield/geometry/mesh_generator.py:47-48`.
- `spacing_x = width_mm / (columns - 1)`; `spacing_y = depth_mm / (rows - 1)` — the same formula as `src/clayfield/terrain/fabrication.py:111-112`.
- The mesh is generated from this grid on demand: `2 * rows * columns` vertices, `4 * rows * columns + 2 * perimeter` faces, base plane at `-base_thickness_mm` (`mesh_generator.py`, `SolidMesh`). The measurement layer never builds that mesh.
- **Effective resolution:** `resolved = 2 * min(spacing_x, spacing_y)`. Two samples are the minimum that can represent a feature; this is the same two-sample rule already reported as `resolved_width` in `fabrication.py:113-114`.

### 1.2 The resolution floor

A feature narrower than `resolved` is a resampling artifact, not a surface feature. Every metric below declares a minimum valid scale, and all of them are multiples of `resolved`:

| Quantity | Minimum valid | Why |
|---|---:|---|
| Feature size (band edges) | `2 × resolved` | A Gaussian band-pass needs at least two samples per feature |
| Roughness scale | `2 × resolved` | Same |
| Anomaly window | `2 × resolved` | A median over fewer than two samples is the sample itself |
| Curvature | feature radius `≥ 2 × resolved` | A second derivative needs enough samples across the feature to be conditioned |

When the user requests a scale below the floor:

- The metric returns **not run** with reason `scale_below_resolution`.
- The panel shows the requested scale and the actual floor, both in mm.
- No mask is generated. The button stays enabled so the user can correct the scale, and the error text names the smallest valid value.

Do not silently clamp the scale to the floor. A clamped request looks like it worked and reports a detection at a scale the user did not ask for.

---

## 2. Mask contract

### 2.1 Representation

One mask type only. Do not add a second.

- A 2D `float32` array, same shape as the heightfield, values in `[0, 1]`.
- `1.0` = fully eligible for cleanup. `0.0` = protected. Intermediate = partial influence.
- Wrap it in the existing `NormalizedField` (`src/clayfield/field/model.py`) so it inherits validation: 2D, ≥ 2×2, floating-point, finite, bounded to `[0, 1]`.
- Serialize as the 16-bit PNG the document format already writes (`project_io.py:462-473`): `np.rint(values * 65535).astype(np.uint16)`.
- The mask is **not** a heightfield and **not** a mesh. It never carries height. A cleanup operation reads it as a selector.

### 2.2 Mapping to geometry

The mask aligns to the heightfield grid 1:1:

```text
mask[i, j]  ↔  heightfield[i, j]  ↔  world (x_j, z_i)
```

No interpolation at the sample level. The mask's sample spacing *is* the heightfield's; if the two shapes differ, the mask is invalid, not resampled silently.

**Validity rule.** A mask is valid when all three hold:

1. `mask.shape == heightfield.shape`.
2. `mask`'s recorded `width_mm`/`depth_mm` equal the heightfield's.
3. The mask's descriptor records the analysis method and parameters that produced it.

A height change without a shape change — a sculpt stroke, a cleanup operation — does **not** invalidate the mask. The grid is unchanged, so the alignment is unchanged. A regeneration that changes the grid does invalidate it.

**On invalidation**, the mask is marked `stale` and the UI must:

- Keep the mask data (do not delete it).
- Refuse to apply it to a cleanup operation.
- Offer *Remap to current grid* (resample with the same interpolation as the heightfield: `cv2.INTER_AREA` for downsampling, `INTER_LINEAR` for upsampling, per `resize_heightfield`) or *Discard*.

Never resample automatically. A remapped mask is an approximation and the user should know it happened.

### 2.3 Mask operations

All distances and radii are in **millimetres**, converted to grid units by the axis spacing. A radius of `r_mm` on a 0.2 mm grid is `r_mm / 0.2` samples.

Let `B = mask > 0.5` — the eligible region — and `d(·)` the Euclidean distance transform with `sampling=(spacing_y, spacing_x)` (`scipy.ndimage.distance_transform_edt`).

| Operation | Definition | Notes |
|---|---|---|
| Replace | `mask = new_mask` | New mask must pass the validity rule |
| Add | `mask = clip(mask + new, 0, 1)` | Union of eligibility, weights accumulate |
| Subtract | `mask = clip(mask − new, 0, 1)` | Removes eligibility |
| Invert | `mask = 1 − mask` | Swaps eligible and protected |
| Expand | `mask = max(mask, d(~B) ≤ r_mm)` | Grows the region by `r_mm`; the new ring gets weight 1 |
| Contract | `mask = mask × (d(B) > r_mm)` | Shrinks the region by `r_mm`; preserves weights inside |
| Feather | `mask = gaussian_filter(mask, sigma=(σ_mm/spacing_y, σ_mm/spacing_x), mode="nearest")` | Soft ramp; `σ_mm` in millimetres |
| Threshold | `mask = B` (1/0) | Re-binarizes at `0.5` unless the user sets another cut |
| Clear | `mask = zeros` | Discards, not "stale" |
| Manual paint | `mask = max(mask, brush_weight)` | Painting never reduces a weight |
| Manual erase | `mask = min(mask, 1 − brush_weight)` | Erasing never increases a weight |

Expand and Contract act on the binary region, so the ring's weight is unambiguous: 1 in, 0 out. Feather is the operation that produces graded weights. Do not implement a "soft expand" — it has no single defensible meaning and the user can feather afterwards.

### 2.4 Mask → geometry blend

The mask selects; the operation transforms. The per-sample influence is:

```text
influence = mask_weight × brush_weight
result    = height + (processed − height) × influence
```

- `processed` is the operation's output on the full field (bilateral, median, a smoothed copy).
- `brush_weight` carries the stroke falloff and the brush strength; a non-brush operation (e.g. "smooth within mask") sets it to 1.
- The result is clamped to the model's physical height bounds. A clamped sample reports as clamped in the status bar; do not let a clamp pass silently.

This mirrors the existing composition blend in `src/clayfield/field/composition.py`: `first + (operation_result − first) * effective_amount`, where `effective_amount = amount * mask.values`. Reuse that arithmetic so the mask behaves the same way in both paths.

**Protected regions are unchanged exactly.** With `mask_weight == 0.0`, the product is `0.0` and `result == height` bitwise. The neighborhood a filter reads may include protected samples — that affects the *processed* value at eligible samples, which is correct — but the protected sample's own height does not move. Assert exact equality in the test, not a tolerance. A tolerance invites a bug where "protected" means "mostly protected".

### 2.5 Viewport overlay contract

`viewport.py` and `gpu_pipeline.py` currently have zero mask references. The overlay is new work; this is its contract.

- The mask uploads as a 2D texture on the same grid as the height texture. Re-upload when the mask changes; keep the geometry VBO static.
- Composite: `color = mix(protected_color, cyan, mask_weight)` with `protected_color = #2A2E35` and `cyan = #62B5C5` (the `accent.primary` token).
- The overlay is a semi-transparent film over the clay: `alpha = opacity × weight_profile`, where the weight profile is the mask's own weight. A weight of 0 still draws the protected film — that is how "protected" becomes visible — but it must be distinguishable from the clay by the film's tint, not by removing the film.
- It never changes the height texture, the vertex positions, or the lighting. A mask view must be readable with the surface's shading intact.
- Show/hide is independent of mask activation. Hiding the overlay does not clear or disable the mask.
- A legend is shown whenever the overlay is visible, naming both states in text, not by colour alone.
- Intermediate weights read as intensity between the two states. Do not map weights through a third colour ramp — the mask's two-state convention is the whole story.

---

## 3. Analysis metrics

### 3.1 Common conventions

- Every metric produces a field on the heightfield grid: `float32`, same shape, in the metric's own units. That field is the heatmap source.
- Every metric produces a binary classification at a user threshold: `value > threshold`, with the comparison's sign stated per metric.
- Every metric converts to a mask by binarizing at the threshold. A weighted conversion is optional: `weight = clip((|value| − T) / (T_full − T), 0, 1)` with `T_full = 2T` by default and overridable in the method parameters. Binarization is the default because it is reproducible and the mask's Feather operation provides the ramp.
- Every metric is deterministic. No random sampling, no seeds in the metric path. The fixture's pseudo-texture uses a fixed analytic pattern, not noise.
- Every metric declares its resolution floor per §1.2 and returns *not run* below it.
- Thresholds below are **initial values calibrated against the fixture in §4**. Changing one means updating the fixture's expected values in the same commit. Do not tune a threshold to make a live model look cleaner — that converts a measurement into a preference.

### 3.2 Detail Size

**Measures:** the amplitude of surface features whose size falls in a requested physical band. It answers "is there a feature between 0.3 and 0.8 mm here?"

**Definition.** Band-pass by difference of Gaussians. The feature size `s` maps to a Gaussian scale `σ = s / 2`, so a blur with `σ = s/2` attenuates features of size `s` by roughly half. This is a convention; state it in the module docstring.

```text
σ_min = s_min / 2        # millimetres
σ_max = s_max / 2        # millimetres
G(σ)  = gaussian_filter(h, sigma=(σ/spacing_y, σ/spacing_x), mode="nearest")
r     = G(σ_min) − G(σ_max)
```

`r` is signed: positive is a local bump in the band, negative a local depression. The band-pass removes the base plane and the large-scale trend, so a flat or tilted model produces `r ≈ 0` and no false positives.

**Parameters.** `s_min`, `s_max` in mm. Defaults `0.3` and `2.0`. `s_min ≥ 2 × resolved`, `s_max ≥ 2 × s_min`.

**Classification.** `|r| > T`, `T` in mm, default `0.02`.

**Valid when.** `s_min ≥ 2 × resolved` and `s_max > s_min`.

**Does not detect.** Features larger than `s_max` (removed by the larger blur), features smaller than the resolution floor, or a smooth ramp of any slope — a ramp survives neither blur and cancels in the difference.

### 3.3 Surface Roughness

**Measures:** how much small-scale height variation a local area carries, independent of the size of the features producing it. It answers "is this area rough?" not "is there a 0.5 mm bump here?"

**Definition.** High-pass then local RMS. The high-pass removes structure larger than the roughness scale; the RMS turns the residual into a per-sample amplitude.

```text
σ_r = roughness_scale / 2                      # millimetres
r   = h − gaussian_filter(h, sigma=(σ_r/spacing_y, σ_r/spacing_x), mode="nearest")
R   = sqrt(uniform_filter(r*r, size=(L_w/spacing_y, L_w/spacing_x), mode="nearest"))
```

`L_w` is the measurement window in mm. `R` is in mm — the RMS height deviation, the roughness analogue of `Ra`.

**Parameters.** `roughness_scale` in mm, default `0.4`. `L_w` in mm, default `2.0`. Both `≥ 2 × resolved`, and `L_w ≥ 2 × roughness_scale`.

**Classification.** `R > T`, `T` in mm, default `0.03`.

**Valid when.** Scales meet the floor; the field is not constant over the window (a constant region gives `R = 0`, which is correct and not a failure).

**Does not detect.** A smooth bump whose curvature radius exceeds the roughness scale — the high-pass leaves almost nothing — or a global tilt. That is the distinction from Detail Size: this metric is blind to feature size and sensitive to amplitude density.

### 3.4 Surface Irregularity

**Measures:** how inconsistent a sample is with its own neighbourhood, normalized by that neighbourhood's own variation. It answers "is this cell an outlier where it sits?" without requiring the user to name a size band.

**Definition.** Robust local z-score against a median level.

```text
m = median_filter(h, size=(L/spacing_y, L/spacing_x), mode="nearest")
s = 1.4826 * median_filter(|h − m|, size=(L/spacing_y, L/spacing_x), mode="nearest")
z = (h − m) / max(s, floor_mm)
```

The `1.4826` factor makes the MAD a consistent estimator of the standard deviation for normal data. The `floor_mm` term is mandatory, not optional: on a perfectly flat plane `s = 0` and a single spike would divide by zero. The floor makes the score finite and scale-relative.

**Parameters.** `L` in mm, default `1.0`. `floor_mm`, default `0.005`. `L ≥ 2 × resolved`.

**Classification.** `|z| > T`, dimensionless, default `3.0`.

**Valid when.** Scales meet the floor. The metric is meaningful on a plane and on a ramp: a linear ramp's median equals the ramp's value, so `z ≈ 0` and the ramp is not flagged.

**Does not detect.** A feature that fills the whole window — if the anomaly is as wide as the median's neighbourhood, the median moves with it and the score collapses. Document this: "the window is the largest anomaly this metric can see; widen it or use Detail Size for larger features."

### 3.5 Curvature

**Measures:** the signed local bending of the surface. Positive is convex up (dome, ridge); negative is concave up (pit, valley). It answers "how tight is this bend, and which way?"

**Definition.** Mean curvature of the heightfield surface, in mm⁻¹, computed on a lightly smoothed field.

```text
h_s  = gaussian_filter(h, sigma=(1.0, 1.0), mode="nearest")   # σ = 1 sample in both axes
h_z, h_x = np.gradient(h_s, spacing_y, spacing_x)             # axis 0 = row = z, axis 1 = column = x
h_xx = np.gradient(h_x, spacing_x, axis=1)
h_zz = np.gradient(h_z, spacing_y, axis=0)
h_xz = np.gradient(h_x, spacing_y, axis=0)
H = ((1 + h_z**2) * h_xx - 2 * h_x * h_z * h_xz + (1 + h_x**2) * h_zz) \
    / (2 * (1 + h_x**2 + h_z**2)**1.5)
```

**Parameters.** Smoothing `σ = 1 sample` (fixed; the second derivative amplifies noise and the raw field is not smooth enough to differentiate twice). No user parameter except the threshold.

**Classification.** `|H| > T`, mm⁻¹, default `0.5`. A threshold of `0.5 mm⁻¹` means "flag any bend with a local radius under 2 mm" — state that equivalence in the panel so the number means something.

**Valid when.** The feature radius is `≥ 2 × resolved`. Below that, the second difference is dominated by sampling and the metric reports *not run*.

**Does not detect.** A flat plane or a ramp (`H = 0`), or a sharp step — a step's curvature is a delta that the one-sample smoothing spreads into a narrow ridge; that is expected and the step should be flagged, not suppressed.

### 3.6 Isolated Peaks

**Measures:** protrusions that stand above their surroundings by a measurable height. It answers "is there a spike here?"

**Definition.** A sample is a peak when it is the local maximum over a footprint *and* its relative height exceeds the threshold.

```text
local_max = maximum_filter(h, footprint=disk(d_p/spacing), mode="nearest")
level     = median_filter(h, size=(L/spacing_y, L/spacing_x), mode="nearest")
peak      = (h >= local_max - eps) & (h - level > T)
```

`eps` absorbs float comparison; `1e-6 mm` is below display and export resolution. `level` is the robust local baseline, not the global mean — a peak on a sloped region must be judged against the slope, not the model's average.

**Parameters.** `d_p` in mm, default `1.0`; `L` in mm, default `2.0`; `L ≥ 2 × d_p`; both `≥ 2 × resolved`.

**Classification.** Binary peak mask; amplitude `h − level` in mm for severity. `T` in mm, default `0.05`.

**Valid when.** Scales meet the floor. The footprint must be smaller than the feature it looks for and larger than the roughness it ignores.

**Does not detect.** Ridges and plateaus — a flat-topped ridge has no local maximum above its own level — or a broad dome whose top spans the footprint. Use Detail Size or Curvature for those.

### 3.7 Depressions

**Measures:** pits and recesses that fall below their surroundings. Exact mirror of Isolated Peaks.

```text
local_min = minimum_filter(h, footprint=disk(d_p/spacing), mode="nearest")
depression = (h <= local_min + eps) & (level - h > T)
```

**Parameters and validity:** as Isolated Peaks. `T` in mm, default `0.05`.

**Does not detect.** Broad valleys, or a depression narrower than the footprint's resolution.

### 3.8 Edge Protection

**Measures:** strong boundaries and transitions that must not be cleaned. It is the one method that produces a **protection** mask rather than an eligibility mask.

**Definition.** Slope from the physical gradient, ramped into a protection weight.

```text
g = hypot(np.gradient(h, spacing_x, axis=1), np.gradient(h, spacing_y, axis=0))   # mm per mm, dimensionless
θ = degrees(arctan(g))
w = clip((θ − θ_min) / (θ_max − θ_min), 0, 1)                                # 1 = protect
edge_mask = 1 − w                                                             # mask convention: 1 = eligible
```

**Parameters.** `θ_min`, `θ_max` in degrees. Defaults `30` and `60`. The ramp is deliberate: a hard threshold produces a one-sample edge line that the mask's Feather then blurs away.

**Classification.** The mask's weight is `1 − w`, so a strong edge gets weight `0` and is excluded from cleanup. Report the detected edge as "protected" in the panel; do not label it "detected defect".

**Valid when.** Scales meet the floor. The slope is a first derivative and is well conditioned at the two-sample limit.

**Does not detect.** A gentle but intentional slope under `θ_min` — it will be treated as eligible. That is the user's risk to set, so show the two angles and their physical meaning (e.g. "30° ≈ 1:1.7").

### 3.9 Combined Detection

**Measures:** the composition of the methods above.

- Inputs: any subset of the eight masks, plus the user's current mask if they include it.
- **ANY** = union: per-sample `max`.
- **ALL** = intersection: per-sample `min`.
- Weighted composition follows the same rule on weights: `max` for ANY, `min` for ALL.
- No node graph, no arbitrary rule builder, no per-method weights in the first release. `GUI_LAYOUT.md` §8 already forbids the node editor; this document forbids the rule builder for the same reason — a rule builder is a second programming language inside a relief tool.

**Valid when.** At least two inputs are selected and each is valid on the current grid. An input that is stale or *not run* cannot be combined; the panel names which one and why.

### 3.10 Metric summary

| Method | Measures | Units | Threshold default | Valid when |
|---|---|---|---:|---|
| Detail Size | Band-limited feature amplitude | mm | 0.02 | `s_min ≥ 2·resolved` |
| Surface Roughness | Local RMS of the high-pass residual | mm | 0.03 | `scale ≥ 2·resolved` |
| Surface Irregularity | Robust local z-score | — | 3.0 | `L ≥ 2·resolved` |
| Curvature | Signed mean curvature | mm⁻¹ | 0.5 | radius `≥ 2·resolved` |
| Isolated Peaks | Local maximum above local level | mm | 0.05 | `d_p ≥ 2·resolved` |
| Depressions | Local minimum below local level | mm | 0.05 | `d_p ≥ 2·resolved` |
| Edge Protection | Slope → protection weight | ° | 30–60 | `≥ 2·resolved` |
| Combined | ANY / ALL of the above | mask | — | ≥ 2 valid inputs |

`resolved = 2 × min(spacing_x, spacing_y)`.

---

## 4. Calibrated fixture

The acceptance gates require "a known test feature at a known physical scale." This is that feature. Implement it as `tests/fixtures/measurement_surfaces.py`; keep the constants in the module, not in the tests.

### 4.1 Geometry

| Parameter | Value |
|---|---|
| Plate | 100 × 100 mm |
| Grid | 501 × 501 → 0.2 mm spacing, `resolved = 0.4 mm` |
| Base height | 0.0 mm |

### 4.2 Defects

All positions in mm from the plate centre. `x` is `column`, `z` is `row`.

| Defect | Placement | Form | Amplitude |
|---|---|---|---|
| Bump | centre `(+25, +25)` | Gaussian, `σ = 0.4 mm` | `+0.30 mm` |
| Pit | centre `(−25, −25)` | Gaussian, `σ = 0.4 mm` | `−0.30 mm` |
| Step edge | line `x = 0` | `0.35 mm` for `x ≥ 0`, `0.0` below | `+0.35 mm` |
| Roughness patch | `x ∈ [20, 30]`, `z ∈ [−30, −20]` | sine grating, 0.8 mm wavelength | `0.08 mm` peak |

The bump's feature size is ≈ 0.8 mm — four samples across, above the floor. The step's slope is `0.35 / 0.2 = 1.75 mm/mm ≈ 60°`. The roughness grating is four samples per cycle, above Nyquist.

### 4.3 No-false-positive plate

A second fixture: the same grid and base with a single 0.2 mm rise over 100 mm in `x` — a tilt of `0.11°`. Nothing should be detected. This is the metric that catches a band-pass or an anomaly score that is really a trend detector.

### 4.4 Expected detections

| Metric | Bump | Pit | Step | Roughness | Tilted plate |
|---|:---:|:---:|:---:|:---:|:---:|
| Detail Size `[0.3, 2.0]` | ✓ | ✓ | ✓ | ✓ | ✗ |
| Surface Roughness | ✗ | ✗ | ✗ | ✓ | ✗ |
| Surface Irregularity | ✓ | ✓ | ✓ | ✓ | ✗ |
| Curvature | ✓ (+) | ✓ (−) | ✓ | ✗ | ✗ |
| Isolated Peaks | ✓ | ✗ | ✗ | ✗ | ✗ |
| Depressions | ✗ | ✓ | ✗ | ✗ | ✗ |
| Edge Protection | ✗ | ✗ | ✓ | ✗ | ✗ |

"✓" means the mask covers the defect's known footprint; "✗" means the covered fraction of the flat region stays under 0.5%. The roughness row for Detail Size is expected because the grating sits inside the band — that is not a false positive, and the test asserts the *flat* region stays clean rather than asserting the roughness patch is missed.

### 4.5 Acceptance assertions

Each metric's test asserts three things, not one:

1. **Recall** — the mask's intersection with the known defect footprint has IoU `≥ 0.6`.
2. **Precision** — the fraction of the flat region marked eligible is `≤ 0.5%`.
3. **Determinism** — two runs on the same input produce bitwise-identical masks.

Plus one test per metric for the resolution floor: a request below `2 × resolved` returns *not run* with `scale_below_resolution`, and produces no mask.

The mask-operation tests use a synthetic rectangular mask on the same grid and assert physical behaviour: an Expand of `2.0 mm` grows the region by `2.0 mm ± 1 sample`; a Feather of `σ = 0.5 mm` produces a ramp whose 10–90 % width is `2.56 σ ± 1 sample`; a Threshold at 0.5 halves the region at the 50 % contour.

The blend test asserts exact equality in protected regions: build a field, a mask with a zeroed rectangle, run the operation, and assert `np.array_equal(result[protected], original[protected])`.

---

## 5. What the builder must not do

These are the failure modes this document exists to prevent. Each has already appeared in the product's own docs as a warning; they are repeated here because the measurement layer is where they bite.

1. **Do not build a mesh in the interaction path.** The heightfield is authoritative; the mesh is generated at the export boundary. A metric that reads a mesh has forked the representation.
2. **Do not clamp a scale request to the floor.** Report *not run*. A clamped request reports a detection at a scale the user did not choose.
3. **Do not normalize a metric to `[0, 1]` and call it the answer.** The metric's units are the product's meaning. A normalized heatmap with no units is decoration.
4. **Do not let a mask survive a grid change without being marked stale.** A misaligned mask silently damages protected geometry.
5. **Do not apply a cleanup outside its mask.** "Mostly protected" is not protected. The blend's zero is exact.
6. **Do not tune a threshold to make a specific model look clean.** Thresholds come from the fixture. If the fixture says a threshold is wrong, change the fixture and the threshold together, in one commit.
7. **Do not add a second mask type, a second grid convention, or a second blend formula.** The document's whole value is that there is one of each.
8. **Do not report a metric as "unsupported" when it is "not run".** The GUI distinguishes them; so must the measurement layer. Unsupported means the representation cannot do it. Not run means the input or scale was invalid.

---

## 6. Open items this document leaves to the builder

These are genuinely open and should be decided with evidence, not guessed:

- **`T_full` per metric.** The default `2T` ramp width is a placeholder; the fixture can calibrate it once one real model has been cleaned. Until then, document the default and expose the override.
- **Curvature's smoothing scale.** Fixed at one sample here to keep the metric reproducible. If the fixture shows the second derivative is too noisy on real models, the scale becomes a documented parameter — not an undocumented tweak.
- **The roughness window default.** 2.0 mm is a starting value chosen to contain at least one cycle of the smallest resolvable feature at 0.2 mm spacing. At coarser grids the window must scale; derive it from `resolved`, not from a constant.
- **Mask overlay shader placement.** A separate pass or a second sampler in the clay fragment shader are both acceptable; the contract in §2.5 is what must hold. Pick one when the viewport work starts and record it in the module docstring.

---

## 7. Cross-references

- Product definition and principles: [`README.md`](README.md)
- Screen, panel, and interaction spec: [`GUI_LAYOUT.md`](GUI_LAYOUT.md) §8–§10
- Visual tokens and mask colours: [`VISUAL_DESIGN.md`](VISUAL_DESIGN.md) §7
- Phase sequence and exit gates: [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md) Phase 3–5
- Verified paths and current-state gaps: [`REPOSITORY_AUDIT.md`](REPOSITORY_AUDIT.md)
- Execution checklist: [`TASK_LIST.md`](TASK_LIST.md)

---

Index: [README.md](../README.md).
