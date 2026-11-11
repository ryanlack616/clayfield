# ClayField web task list

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked.

Design: [README.md](README.md). Roadmap: [ROADMAP.md](ROADMAP.md). Shared docs:
[../docs/README.md](../docs/README.md). Core build:
[../mesh-forge/TASK-LIST.md](../mesh-forge/TASK-LIST.md).

Rule: design changes go in the plan; status changes go here.

---

## Decisions (blocking)

### Before D0
Decided 2026-11-11; answers in README §0. CF-1/2/3/6 are recorded in
[ADR-0001](../docs/adr/0001-v4-projects-read-only.md); the rest are accepted as
recommended. Reopen only by superseding §0 with a new date plus an ADR.
- [x] CF-1 Desktop parity scope — keep recent projects, themes, cross-section, export preview; drop ComfyUI, presets, crop/resize
- [x] CF-2 v1–v4 compatibility — v4 projects open read-only; no lossy migration
- [x] CF-3 Terrain noise — dropped; v4 projects with `noise_amplitude > 0` read-only
- [x] CF-4 Color policy (sRGB default, no ICC, 16-bit preview tone map)
- [x] CF-5 Units (millimetres only in v1)
- [x] CF-6 Crop/resize — dropped; v4 projects using `image_geometry` read-only
- [x] CF-7 Browser support matrix + minimum versions
- [x] CF-8 Mobile/touch support (desktop-first; graceful degradation)
- [x] CF-9 Hosting provider + COOP/COEP/CSP header capability
- [x] CF-10 PWA update strategy (prompt; rollback path)
- [x] CF-11 "v5" semantics — document schema version; container version separate

---

## App phases

### D0 — Decode + grayscale  (needs core C8a)
Refs: README §3, §4, §9, §10
- [ ] `@clayfield/relief` + `clayfield-relief` + `clayfield-wasm` scaffold
- [ ] Image decode (PNG/JPEG/TIFF/BMP; 16-bit → f32; EXIF transpose)
- [ ] Grayscale (Rec.601 / Rec.709 linear-light; channel/color policy)
- [ ] `pipeline.worker`
- [ ] Parity harness + fixtures in CI
- [ ] **Exit:** decode/grayscale parity (8-bit exact, 16-bit); fixtures green

### D1 — PROCESS
Refs: README §3, §9
- [ ] levels, curves (banker's rounding), tone, blur (reflect-101), sharpen (9×9 σ1.0), threshold, invert
- [ ] Debounce + stale-generation cancel
- [ ] **Exit:** all adjustment parity; cancellation

### D2 — Height mapping + analysis
Refs: README §3, §4, §10
- [ ] `height.map` normalized → mm
- [ ] Fabrication analysis + profiles + warnings
- [ ] Resource budgets + 2048 cap + preflight
- [ ] **Exit:** mm parity; warning order matches; cap enforced

### D3 — Viewport plugins  (needs core C4, D2)
Refs: README §6
- [ ] `HeightDisplacementMaterial`, `HeightRampColoring`, `BrushRingOverlay`, `HeightfieldPickProvider`
- [ ] Camera presets, shading toggles
- [ ] **Exit:** 60 fps @ 512²; picking parity; plugins registered

### D4 — Sculpt  (needs C2, C3 multi-buffer, D2, D3)
Refs: README §5, §10
- [ ] Laplacian/Taubin/bilateral kernels, falloffs, brush query/stroke
- [ ] SAB worker, dirty rects, patch undo, brush ring
- [ ] Resolution-change discard + status
- [ ] **Exit:** dab parity; ≥30 Hz @ 2048²; bounded history

### D5 — Mesh + export  (needs core C5, D4)
Refs: README §3, §10
- [ ] `mesh.solid`, `mesh.container`, `mesh.orient`
- [ ] STL/3MF via `@mesh-forge/export`; heightmap via a domain `Exporter`
- [ ] Verification; progress/cancel
- [ ] **Exit:** byte-identical STL; 3MF opens in slicer/lib3mf

### D6 — Persistence + migration  (needs C2, C6, D5)
Refs: README §8, §19
- [ ] `document.json` schema + migrations
- [ ] v5 save/load; v1–v4 policy; sparse sculpt codec; v4 NPZ path
- [ ] Checksums, atomic save, autosave/recovery, multi-tab, FSA, quota, blob GC
- [ ] **Exit:** round-trip; corrupt/malicious archive rejected; no silent data loss

### D7 — App shell + layout  (needs C2, C4, C7, D3–D6)
Refs: README §7
- [ ] Floating `SourceImageCard` upper-left (drag/resize, persisted, Original/Processed)
- [ ] Left: upload + PROCESS + brush; center: viewport; right: fabrication
- [ ] Camera toolbar, cross-section, export dialog, recent projects
- [ ] **Exit:** layout matches spec; keyboard/a11y pass

### D8 — Hardening + release  (needs C3, C4, C5, C6, C8b)
Refs: README §14–§21
- [ ] PWA (manifest, service worker, offline, update strategy)
- [ ] no-SAB fallback; Safari/iOS; cross-browser matrix
- [ ] Security (CSP/COOP/COEP/SRI), fuzz, perf gates
- [ ] Observability, diagnostics/support bundle, error codes
- [ ] **Exit:** offline start; installable; matrix green; security/fuzz clean

---

## Cross-cutting gates (apply per phase)

- [ ] Tests: unit/property/golden/contract/E2E/visual
- [ ] Lint/format/typecheck
- [ ] Security: input limits, headers, dependency audit
- [ ] Performance: budgets measured, no regressions
- [ ] Accessibility: keyboard + axe + manual pass
- [ ] Docs/plan/ADR updated

## Done log

- 2026-11-11 — CF-1…CF-11 accepted (D0 decision gate satisfied). ADR-0001 sets
  v4 projects to read-only and drops presets, crop/resize, and terrain noise.
- (append completed phases with date and notable decisions)
