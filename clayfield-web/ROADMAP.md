# ClayField web roadmap

App build sequence on the mesh-forge core. Full design: [README.md](README.md).
Status: [TASK-LIST.md](TASK-LIST.md). Core build:
[../mesh-forge/ROADMAP.md](../mesh-forge/ROADMAP.md). Shared policies:
[../docs/README.md](../docs/README.md).

## Goal

A client-side web version of ClayField (image → relief → sculpt → STL/3MF),
built as the first app on the mesh-forge core.

## App track

```
D0  Decode + grayscale           (needs core C8a)
D1  PROCESS
D2  Height mapping + analysis
D3  Viewport plugins             (needs core C4)
D4  Sculpt                       (needs C2, C3 multi-buffer, D2, D3)
D5  Mesh + export                (needs C5, D4)
D6  Persistence + migration      (needs C2, C6, D5)
D7  App shell + layout           (needs C2, C4, C7, D3–D6)
D8  Hardening + release          (needs C3, C4, C5, C6, C8b)
```

## How it interlocks with the core

```
core:  C0 → C1–C3 → C8a ─────────────► D0–D2
                       C4 ───────────► D3
                       C5 ───────────► D5
                       C6 ───────────► D6
                       C7 ───────────► D7
                       C8b (depends on C4–C7; independent of ClayField; then D8)
```

D0 cannot start until C8a partially freezes the consumed contracts. See
[../mesh-forge/ROADMAP.md](../mesh-forge/ROADMAP.md) for the core critical path.

## Milestones

| Milestone | Meaning |
|---|---|
| M1 — Image + PROCESS (D1) | Upload and adjust an image in the browser |
| M2 — First 3D preview (D3) | Heightfield rendered in the viewport |
| M3 — Sculpt (D4) | Interactive smoothing at target latency |
| M4 — Export (D5) | Valid STL/3MF from the browser |
| M5 — Projects + layout (D6–D7) | Save/load, final UI |
| M6 — Release-ready (D8) | PWA, fallbacks, security, cross-browser |

## Effort

~22–28 person-weeks with 20–30% contingency (solo, part-time), minus 6–10 weeks
of overlap with the core. See
[../docs/planning/delivery-and-risks.md](../docs/planning/delivery-and-risks.md).

## Scope guardrails

- Image upload only; no procedural/QFractalNow/composition/ComfyUI.
- Left: upload + PROCESS + brush; center: viewport; right: fabrication; floating
  source card upper-left.
- ≤2048² authoritative heightfield; streamed export.
- `evaluated = base + sculptOffsets`; export reads the evaluated field.
