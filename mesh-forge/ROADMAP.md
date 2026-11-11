# mesh-forge roadmap

Core build sequence. Full design: [README.md](README.md). Status:
[TASK-LIST.md](TASK-LIST.md). Shared policies: [../docs/README.md](../docs/README.md).
The consuming app is tracked in [../clayfield-web/ROADMAP.md](../clayfield-web/ROADMAP.md).

## Goal

A small, domain-agnostic engine for client-side WebGL2 field/mesh workbench
tools. ClayField is its first consumer; the core must never import or reference
ClayField/relief concepts.

## Core track

```
C0  Foundations (workspace, toolchain, boundaries, CI)
C1  Primitives + taxonomy
C2  Document + undo
C3  Transport + WASM ABI
C8a Partial freeze (consumed contracts)   <-- unblocks ClayField D0
C4  Renderer + viewport
C5  Export framework
C6  Persistence
C7  UI primitives
C8b Full-stack reuse proof
```

## Critical path

C0 → C1–C3 → **C8a** → (ClayField D0–D2) → C4–C7 → C8b → ClayField D8.

C8a is the partial freeze point: ClayField builds against the frozen C1–C3
subset and never chases a moving core. C8b is the full-stack reuse proof with
`apps/mesh-lab`; it depends on C4–C7 and may only require additive changes to the
C8a subset.

## Milestones

| Milestone | Meaning |
|---|---|
| M1 — Partial contracts frozen (C8a) | ClayField can start D0 |
| M2 — Renderer (C4) | `SceneSnapshot` viewport + plugin registries |
| M3 — Export + persistence + UI (C5–C7) | Core feature-complete |
| M4 — Reuse proven (C8b) | mesh-forge validated by mesh-lab; no changes required to the C8a subset |

## Effort

~20–26 person-weeks with 20–30% contingency (solo, part-time). See
[../docs/planning/delivery-and-risks.md](../docs/planning/delivery-and-risks.md).

## Guardrails

- Core never imports a domain/app package.
- No domain terms in core (`relief`, `heightfield`, `sculpt`, `fabrication`)
  except tests/fixtures. STL and 3MF are generic mesh formats, not domain terms.
- mesh-lab consumes **packed** packages, not workspace source.
- After C8a, API changes are additive + versioned.
