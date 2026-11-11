# ClayField on mesh-forge — Implementation Plan

Status: draft for review. Docs index: [../docs/README.md](../docs/README.md).
Companion doc: [../mesh-forge/README.md](../mesh-forge/README.md).

ClayField is the first consumer of the mesh-forge core. This plan covers only
domain code; all engine infrastructure comes from `@mesh-forge/*` and
`mesh-forge-core`. If a core change is needed it is a versioned additive change to
mesh-forge, never a fork.

This plan reflects a contract review that found the original ClayField plan
mapped several non-transform capabilities onto `Operation`. The corrected
capability taxonomy (§3) and the unit/space model (§4) are the most important
changes.

---

## 0. Decisions needed before D0

| # | Decision | Recommendation |
|---|---|---|
| CF-1 | Desktop feature parity scope: presets, crop/resize, cross-section, export preview, recent projects, dark theme, ComfyUI | Keep: recent projects, dark theme, cross-section, export preview. Drop: ComfyUI. Decide presets and crop/resize (see §11). |
| CF-2 | Project compatibility: v1–v4 desktop projects | Open v4 with a clear unsupported-feature policy; reject or read-only for features dropped from web v1. Do not silently lose data. |
| CF-3 | Terrain noise stage (in `terrain/heightfield.py`) | Decide in/out. If kept, replace with a deterministic, cross-platform RNG and pin it in fixtures. |
| CF-4 | Color policy | sRGB by default, optional linear-light; no ICC transforms in v1; document 16-bit preview tone mapping. |
| CF-5 | Units | Millimetres only in v1; label clearly. |
| CF-6 | Crop/resize | Keep if v4 projects must round-trip `image_geometry`; otherwise drop and reject v4 projects that use it. |
| CF-7 | Browser support matrix | Primary: current Chrome/Edge. Secondary: Firefox + Safari (WebGL2, no SAB). Define a minimum-version policy and a graceful-degradation path. |
| CF-8 | Mobile/touch support | Desktop-first. On touch, support pinch/pan and avoid hover-only interactions; lower default resolution. Not a v1 gate. |
| CF-9 | Hosting + headers | Static host that can set COOP/COEP/CSP (e.g., Cloudflare Pages/Netlify/Vercel); GitHub Pages cannot, so it uses the no-SAB fallback. |
| CF-10 | PWA update strategy | Prompt to reload on new build (never silently reload mid-edit); keep the previous build deployable for rollback. |
| CF-11 | "v5" semantics | Define whether "v5" means the container version or the document schema version; keep them independent and documented. |

---

## 1. Scope

### In scope
- Single image upload as the only source.
- Full PROCESS: levels, curves, brightness/contrast, blur, sharpen, threshold,
  invert, grayscale/linear-light.
- Height mapping to physical millimetres.
- Sculpt smoothing brush (Laplacian/Taubin/bilateral) with patch undo.
- Solid mesh + container/walls, orientation for print.
- STL/3MF/PNG/TIFF export with verification; export preview.
- Cross-section inspection.
- Project save/load/autosave; recent projects; desktop v4 import policy.
- Light and dark themes.
- Final layout: floating source card upper-left; left = upload + PROCESS + brush;
  center = viewport; right = fabrication.

### Out of scope (dropped from desktop)
Procedural generators, QFractalNow + binary, composition/secondary/mask,
ComfyUI, batch/headless adapter.

---

## 2. Packages

```
clayfield/
├─ packages/
│  ├─ relief/          @clayfield/relief  (schemas, ops, presets?, domain types)
│  └─ app/             @clayfield/app     (Vite PWA, layout, stores, worker wiring)
└─ crates/
   ├─ clayfield-relief/   image/terrain/sculpt/geometry/export domain
   └─ clayfield-wasm/     ClayField ABI (depends on mesh-forge-core/-wasm)
```

Dependency direction: `@clayfield/relief → @mesh-forge/*`;
`@clayfield/app → everything`. Never the reverse. `clayfield-wasm` depends on
`mesh-forge-core` and `mesh-forge-wasm`; the reverse is forbidden.

---

## 3. Capability mapping (corrected taxonomy)

ClayField's capabilities map to the mesh-forge contracts as follows. **Only the
rows marked Operation go in the pipeline stack.**

| Capability | mesh-forge contract | Notes |
|---|---|---|
| `image.decode` | `SourceAdapter` / host | `createImageBitmap` for PNG/JPEG/BMP; `@clayfield/relief` 16-bit TIFF decoder → f32; EXIF transpose |
| `image.grayscale` | `Operation` | Rec.601 non-linear / Rec.709 linear-light; alpha ignored |
| `image.levels` | `Operation` | |
| `image.curve` | `Operation` | 4096 LUT; banker's rounding |
| `image.tone` | `Operation` | brightness/contrast/gamma |
| `image.blur` | `Operation` | reflect-101; kernel `max(3, round(r*6)|1)` |
| `image.sharpen` | `Operation` | 9×9 Gaussian σ1.0 on f32 |
| `image.threshold` | `Operation` | `>=` cutoff |
| `image.invert` | `Operation` | image pipeline inverts first |
| `height.map` | `Operation` (domain) | normalized → physical mm; unit-bearing wrapper |
| `sculpt.smooth` | `Command` (interactive domain) | operates on `Heightfield`; a stroke is a patch command, not a batch pipeline stage |
| `sculpt.pick` | `Query` | ray → `Hit`; worker-owned |
| `mesh.solid` | `Operation` | field → mesh |
| `mesh.container` | `Operation` | mesh → mesh |
| `mesh.orient` | `Operation` | mesh → mesh |
| `export.stl` / `export.3mf` | `Exporter` (thin adapter over `@mesh-forge/export`) | no reimplementation |
| `export.heightmap` | `Exporter` (domain) | PNG/TIFF 8/16-bit |
| `analyze.fabrication` | `Analyzer` | metrics + warnings |
| `analyze.crossSection` | `Analyzer` / TS | UI-only profile extraction |

---

## 4. Units and spaces

ClayField defines branded wrappers over mesh-forge buffers:

- `NormalizedField` — 0..1 image/height source.
- `Heightfield` — physical millimetres (the authoritative ≤2048² grid).

`height.map` accepts `NormalizedField` and produces `Heightfield`. `sculpt.*`
operates on `Heightfield`. Core `Field2D` stays unitless.

Invariant: `evaluated = base + sculptOffsets` in millimetres; export reads the
evaluated heightfield.

---

## 5. Document payload

Node kind `relief` with payload:

```
{
  source: { kind: "image", blobRef, decodedHash, width, height },
  process: OperationInstance[],          // PROCESS stack
  geometry: { crop?: ..., resize?: ... }, // if CF-6 keeps crop/resize
  heightMapping: {...},
  sculpt: { offsetRef, resolution, settings },  // domain payload field, not a core Layer
  fabrication: { baseThickness, reliefMode, profile, container },
  resolution: { rows, cols }
}
```

Sculpt is a **domain payload field**, not a generic core `Layer` and not a
pipeline operation. Evaluation order is defined by the ClayField evaluator:

```
base = decode → process → height.map
evaluated = base + sculptOffsets
```

Base-change behavior:
- Parameter changes keep the sculpt layer.
- Resolution changes cannot map the layer → discard it with a status message
  (matches desktop behavior).

---

## 6. Renderer plugins

Registered with mesh-forge `@mesh-forge/render` registries (no renderer edits):

- `HeightDisplacementMaterial` — R32F height texture via `texelFetch`, render in
  millimetres, central-difference normals.
- `HeightRampColoring` — material feature/uniform set for low/high colour mix.
- `BrushRingOverlay` — `LINE_LOOP` sampled on the visible heightfield.
- `HeightfieldPickProvider` — delegates ray to `clayfield-wasm` `Query`.

---

## 7. UI layout (locked)

- **Upper-left overlay:** `@mesh-forge/ui` `FloatingCard` (controlled
  position/size, persistence callback) wrapping `SourceImageCard`: decoded image
  letterboxed on a 2D canvas, filename + px dimensions, `Original | Processed`,
  collapse/close. Persisted to `localStorage` + IndexedDB; z-index above canvas,
  below modals; must not intercept viewport orbit/zoom.
- **Left panel:** `ImageUpload` → `ProcessPanel` (histogram, curve editor, levels,
  tone, blur, sharpen, threshold, invert, grayscale, reset) → `SculptControls`
  (on/off, radius, strength, falloff, algorithm).
- **Center:** `ViewportHost` + domain materials/overlays + camera-preset toolbar.
- **Right panel:** `FabricationPanel` (dimensions, height/mapping, base, relief
  mode, profile, container, resolution, analysis, export).

---

## 8. Persistence

- Container from `@mesh-forge/persistence`; ClayField supplies `AppSchema` (zod)
  and migrations via `SchemaRegistry`.
- Blobs: original source bytes; versioned sparse `sculpt_offsets` codec
  (`codec`, `dtype`, `shape`, `hash`, sparse rows/cols/values).
- Versions: container version, `DocumentEnvelope.schemaVersion`, per-op version
  are distinct. Define which number "v5" refers to.
- Desktop migration:
  - Support v1–v4 per an explicit policy (migrate / reject / read-only).
  - v4 features dropped from web (procedural, QFractalNow, composition,
    crop/resize) must not be silently discarded.
  - v4 `sculpt_offsets.npz` requires a migration path (zip.js + minimal `.npy`
    parser in `@clayfield/relief`) or a documented rejection.
  - Preserve unknown fields when saving if read-only migration is offered.

---

## 9. Parity harness (moved earlier)

Golden fixtures and parity tests belong in **D0–D2**, not D8.

Fixtures generated from the Python app, pinned to a specific Python environment:

- grayscale/channel order (BGRA vs RGBA, Rec.601/709)
- levels/curve rounding (banker's rounding)
- blur kernel size + reflect-101
- sharpen 9×9 σ1.0
- threshold `>=`
- adjustment order: invert → levels → curve → brightness/contrast → blur →
  sharpen → threshold
- height mapping order and mm output
- noise determinism (if kept)
- picking (ray/heightfield units, bisection)
- matrix convention (row-major desktop vs column-major gl-matrix)

Run fixtures against both SIMD and scalar WASM builds with documented tolerances.

---

## 10. Phases

| Phase | Depends on | Deliverable | Exit criteria |
|---|---|---|---|
| **D0** | C1, C3, **C8a** | Domain scaffold, image decode + grayscale, `pipeline.worker`, parity harness | Decode/grayscale parity (8-bit exact, 16-bit); channel/color policy verified; fixtures in CI |
| **D1** | D0 | Full PROCESS stack + debounce/cancel | All adjustment parity; stale generation cancelled |
| **D2** | D1 | Height mapping + fabrication analysis + budgets | mm parity; warning order matches; 2048 cap enforced; terrain-modifier decision applied |
| **D3** | C4, D2 | Viewport materials/overlays/pick provider | 60 fps at 512²; picking parity; custom plugins registered |
| **D4** | C2, C3 (multi-buffer SAB), D2, D3 | Sculpt engine + SAB worker + patch undo + brush ring | Dab parity; ≥30 Hz at 2048²; bounded history; resolution-change discards layer |
| **D5** | C5, D4 | Mesh + container + orient + STL/3MF/heightmap | Byte-identical STL; 3MF opens in lib3mf/slicer; progress/cancel; verification |
| **D6** | C2, C6, D5 | Document schema, save/load, v1–v4 migration, autosave | Round-trip; corrupt/malicious archive rejected; unsupported-feature policy enforced; recovery |
| **D7** | C2, C4, C7, D3–D6 | App shell + locked layout | Layout matches §7; card drag/resize persists; controlled `FloatingCard` |
| **D8** | C3, C4, C5, C6, C8b | PWA, no-SAB fallback, Safari/iOS, parity/fuzz, security, release | Offline start; installable; cross-browser matrix; security/fuzz clean |

**Sequencing:** D0–D2 start after **C8a** (partial freeze). C4–C7 proceed
sequentially (interleaved for a solo developer); D3–D7 consume them. D8 starts
after C8b. This ordering removes the original "API frozen too late" conflict.

---

## 11. Open scope decisions

- **Presets** — desktop ships them. Either keep as a JSON import/export in
  `@clayfield/relief` or explicitly drop for v1.
- **Crop/resize** — keep if v4 `image_geometry` must round-trip; otherwise drop
  and reject v4 projects that use it.
- **Cross-section** — keep (listed as `analyze.crossSection`); it is a shipped
  desktop feature.
- **Export preview** — keep (desktop feature; the `ExportDialog` shell exists).
- **Terrain noise** — decide in/out; if in, deterministic RNG + fixtures.

---

## 12. Acceptance criteria

- Image-only source; no procedural/composition/QFractalNow code paths.
- PROCESS controls + brush on the left; fabrication on the right; floating card
  upper-left.
- Numerical parity with the Python app for every ported algorithm (documented
  tolerances for SIMD).
- Sculpt is smoothing-only; stroke = one undo entry; base changes preserve the
  layer; resolution changes discard it with a warning.
- Export reads the evaluated heightfield; STL/3MF pass validation and slicer QA.
- Project round-trip and v4 import policy honored without silent data loss.
- 2048² authoritative cap enforced with memory preflight.
- No domain code in `@mesh-forge/*`; no deep imports; packed-package test passes.

---

## 13. Risks

| Risk | Mitigation |
|---|---|
| Scope creep from desktop parity | §11 decisions locked before D1; explicit drop list |
| Sculpt performance at 2048² | Multi-buffer SAB, dirty rects, worker-owned history, profiling gate in D4 |
| Large-mesh export memory | Streaming `ExportSink`, u32 indices, default export 1024², 2048² with warning |
| v4 data loss | Explicit unsupported-feature policy + fixtures + read-only option |
| Color/16-bit parity | Fix channel/color policy in D0; fixtures both 8/16-bit |
| Parity drift (SIMD) | Dual-build golden tests with tolerances |
| Renderer fork | Use mesh-forge registries; custom-plugin test in D3 |
| Persistence fork | Register `AppSchema`; second-app schema test in C6 |
| Undo memory | Patch/blob commands; byte-capped history |
| API churn | Build only against C8a-frozen subset |

---

## 14. Quality gates and CI

- Test strategy: `../docs/quality/test-strategy.md` (unit, property, golden/parity,
  contract, E2E, visual, performance, security, a11y).
- Parity fixtures are generated from the Python app with a pinned environment and
  run against **both SIMD and scalar** WASM builds.
- CI (once the workspace exists): typecheck, lint/format, unit/property,
  contract/ABI, a small E2E smoke, parity fixtures, docs link check.
- Gates become blocking once baselines are stable; performance/security start as
  warnings.
- Desktop app remains the reference implementation and fixture source until web
  parity is reached.

## 15. Security and privacy

- Threat model: `../docs/security/threat-model.md` (archives, images, worker
  messages, WASM, CDN, multi-tab).
- Untrusted input limits: archive members/size/ratio, image dimensions/bytes,
  JSON schema + size, worker message validation.
- CSP/COOP/COEP/CORP/HSTS/SRI configured at the static host; `wasm-unsafe-eval`
  scoped for WASM compilation.
- No telemetry by default; local-only guarantee documented in `../PRIVACY.md`.
- v4 import is an untrusted-input path: validate members, hashes, and the NPZ
  parser.
- Security acceptance criteria in D0 (image budgets), D6 (archives/migration),
  D8 (CSP/fuzz/headers).

## 16. Observability and support

- Structured logging with redaction; error boundaries around the app shell.
- Stable error codes (`../docs/reference/error-codes.md`) with translatable
  messages and recovery actions.
- Diagnostics panel: app/build version, browser/OS, WebGL capabilities, WASM
  ABI/core/opset, feature flags, recent codes.
- Redacted support-bundle export; never include project content.
- Runbooks: `../docs/operations/runbooks.md`.

## 17. Accessibility and i18n

- WCAG 2.2 AA target (see `../docs/accessibility/a11y-plan.md`).
- Canvas exposes dimensions/height range/warnings as text; ARIA live regions for
  progress and errors.
- Keyboard-only path for upload, PROCESS, brush, camera, card move/resize, and
  export.
- Reduced motion, contrast, light/dark themes.
- i18n-ready strings and `Intl` formatting (`../docs/i18n/i18n-plan.md`);
  millimetres only in v1, labelled.

## 18. Performance and resource budgets

- Numeric targets: `../docs/performance/budgets.md` (bundle, WASM, first load,
  frame time, sculpt p95, export time, peak memory, storage).
- Preflight and reject >2048² with a clear code; 2048² is the authoritative cap.
- Dirty-rect texture updates during sculpt; streamed exports; backpressure.
- OOM and GPU context loss are recoverable UX states.
- Measure at D3 (frame time), D4 (dab latency), D5 (export/memory), D8 (load).

## 19. Data integrity and UX robustness

- Checksums, atomic save, autosave/recovery, unknown-version read-only (see
  `../docs/data/project-integrity.md`).
- Multi-tab writer election; second tab read-only.
- FSA permission re-prompt; OPFS/download fallback.
- Storage quota handling and `persist()`.
- Blob dedup + orphan GC.
- v4 unsupported-feature policy: migrate, reject, or read-only — never silently
  lose data.
- Loading/empty/error/offline/read-only/onboarding states designed.

## 20. Legal and licensing

- Dependency audit and allowlist: `../docs/legal/license-policy.md`.
- Desktop PySide6 is LGPL (dynamic linking); web drops `fractalnow`.
- `NOTICE` finalized before public release.
- Confirm `ClayField` name/trademark before publishing.
- Fonts/icons/assets licensed and attributed.

## 21. Delivery, rollout, and desktop sunset

- Effort, critical path, feature-parity matrix, risk register, and rollout:
  `../docs/planning/delivery-and-risks.md`.
- Solo, part-time; ranges with 20–30% contingency.
- Locked cut list for v1; additions require an ADR and a parity-matrix update.
- Staged rollout if published: personal → private preview → small beta → public.
- Desktop is not sunset until web parity and stability; keep it as the fixture
  source.

## 22. Documentation and developer experience

- Web user guide derived from `../docs/user_guide.md`; v4→v5 migration guide.
- Architecture overview and data-flow diagrams.
- WASM debugging guide (source maps, symbols, panic hooks).
- Glossary of domain terms (relief, heightfield, sculpt, fabrication).
- Docs CI (link check, markdownlint); keep plans and ADRs current.
