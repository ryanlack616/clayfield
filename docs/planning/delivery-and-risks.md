# Delivery plan and risks

Personal-project scale: one developer, part-time. Estimates are ranges with
contingency, not commitments.

## Effort (from the two plans)

| Area | Estimate |
|---|---|
| mesh-forge core (C0–C8b) | ~20–26 planning; 18–28 conservative (per-phase sum) |
| ClayField on mesh-forge (D0–D8) | ~22–28 person-weeks |
| Overlap (core phases reused) | roughly 6–10 weeks saved |
| **Combined, after overlap** | **~32–48 person-weeks** (42–54 minus 6–10) |
| Contingency | +20–30% → ~38–62 person-weeks |

The combined figure is the only number that should be quoted to anyone outside
the project; the per-area ranges are for sequencing, not for commitments.

Highest-risk, highest-effort items: **sculpting interactivity (D4)** and
**large-mesh streaming export (D5)**. Do not run them alongside major UI churn.

## Critical path

C0 → C1–C3 → **C8a (freeze)** → D0–D2 → C4–C7 (sequential, interleaved) → D3–D7 → C8b → D8.

## Feature parity matrix (desktop → web v1)

| Feature | Web v1 |
|---|---|
| Image upload + PROCESS | Yes |
| Procedural generators | No (dropped) |
| QFractalNow | No (dropped) |
| Composition/secondary/mask | No (dropped) |
| Height mapping + fabrication | Yes |
| Sculpt smoothing brush | Yes |
| Container/walls | Yes |
| STL/3MF/PNG/TIFF export | Yes |
| Cross-section | Keep |
| Export preview | Keep |
| Presets | No (dropped; ADR-0001) |
| Crop/resize | No (dropped; v4 projects using it open read-only) |
| Terrain noise | No (dropped; v4 projects with `noise_amplitude > 0` open read-only) |
| Recent projects | Keep |
| Dark theme | Keep |
| ComfyUI | No (dropped) |

## Risk register

| Risk | Probability | Impact | Trigger | Mitigation |
|---|---|---|---|---|
| Sculpt too slow at 2048² | Medium | High | p95 > 33 ms | Dirty rects, GPU compute if needed, lower default res |
| Export memory blowup | High | High | OOM at 2048² | Stream, u32 indices, default 1024², preflight |
| v4 project data loss | Medium | High | Unsupported features | Explicit policy, read-only, fixtures |
| SIMD/scalar parity drift | Medium | Medium | Fixture mismatch | Dual-build tests + tolerances |
| Core/app boundary leaks | Medium | High | Domain code in core | Lint, packed-package test, ADR gate |
| Scope creep from parity | High | Medium | New "small" features | Locked cut list; ADR for additions |
| Licensing surprise | Low | High | GPL dep found | License allowlist + scan |
| Motivation/time | High | Medium | Long gap | Small milestones, keep a working vertical slice |

## Rollout (if ever published)

1. Local/personal use.
2. Private preview link (static host with headers).
3. Small beta (TestFlight/PWA) if desired.
4. Public, only after security/licensing/accessibility review.

Feature flags: keep optional/large features behind a flag so a bad build can be
disabled without redeploying.

## Desktop sunset

No longer a sunset path. ADR-0002 makes desktop V3 the active product and the web
track parallel, so the desktop app is not being retired. The web track keeps this
parity matrix for its own scope; the desktop app stays the product.

---

Part of the web track docs. Index: [docs/README.md](../README.md).
