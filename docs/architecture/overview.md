# Architecture overview

Data-flow and boundary reference for the two web builds. Design lives in
[`../../mesh-forge/README.md`](../../mesh-forge/README.md) and
[`../../clayfield-web/README.md`](../../clayfield-web/README.md); this page is the
map, not the contract.

## Repo topology

```
clayfield/                      # monorepo root
├─ mesh-forge/                  # domain-agnostic core
│  ├─ packages/                 # @mesh-forge/* (TS)
│  ├─ crates/                   # mesh-forge-core, mesh-forge-wasm (Rust)
│  ├─ apps/mesh-lab/            # reuse proof (packed packages)
│  └─ contracts/                # C8a frozen artifacts
├─ clayfield-web/               # first consumer (app plan D0–D8)
└─ docs/                        # shared policies (this directory)
```

`mesh-forge` and `clayfield-web` are siblings. The core never imports the app;
the app imports the core. Shared policies live in `docs/`.

## Core/app boundary

| Layer | Owns | Must not own |
|---|---|---|
| `mesh-forge-core` (Rust) | buffers, transforms, pipeline, cancellation, export sink, ABI descriptors, `MF-*` error codes | image codecs, domain exporters/analyzers, relief semantics |
| `mesh-forge-wasm` (Rust) | `#[repr(C)]` descriptors, bytemuck, handle ABI, capability aggregation | domain ops |
| `@mesh-forge/*` (TS) | math, buffers, geometry, document, render, viewport-react, export, transport, persistence, wasm-host, ui | ClayField/relief concepts |
| `@clayfield/*` (TS) | image decode, PROCESS, height mapping, sculpt, mesh, fabrication analysis, persistence schema | renderer internals, core transport |
| `clayfield-relief` / `clayfield-wasm` (Rust) | domain ops and ClayField ABI | core buffers/pipeline |

The dependency direction is one-way: `@clayfield/* → @mesh-forge/*` and
`clayfield-wasm → mesh-forge-core/-wasm`. The reverse is forbidden.

## Data flow

```
image bytes
  → host decode (createImageBitmap; @clayfield/relief 16-bit TIFF)
  → NormalizedField (0..1)
  → PROCESS stack (invert → levels → curve → tone → blur → sharpen → threshold)
  → height.map (normalized → mm)
  → base Heightfield
  → base + sculptOffsets = evaluated Heightfield
  → mesh.solid → mesh.container → mesh.orient
  → STL / 3MF / heightmap / PNG / TIFF
```

`evaluated = base + sculptOffsets` is the invariant. Export reads the evaluated
field. Sculpt offsets live in the app payload, not in a core `Layer`.

## Contract taxonomy

| Contract | Responsibility |
|---|---|
| `SourceAdapter` / `Importer` | host bytes or file → `ImageBuffer` / `Field2D` / `MeshBuffers` |
| `Operation` | field→field or mesh→mesh **batch transform** (pipeline stage only) |
| `Query` | ray pick, sample, measure (not a pipeline stage) |
| `Exporter` | terminal export via `ExportSink` |
| `Analyzer` | metrics and warnings |
| `Pipeline` | ordered transforms only, cancellable/budgeted |
| `Command` | undo unit; patches or blob refs; interactive edits such as a sculpt stroke |

`OperationSpec` is a linear stack of `OperationInstance`. `Query`, `Exporter`,
`Analyzer`, and interactive `Command`s are invoked explicitly, never placed in
the pipeline stack.

## Package dependency graph

```
math:            (none)
buffers:         math
geometry:        math, buffers
document:        math, buffers
render:          math, buffers, geometry
viewport-react:  math, buffers, geometry, render
export:          math, buffers, geometry
transport:       math, buffers
persistence:     math, buffers, document
wasm-host:       mesh-forge-core, mesh-forge-wasm
ui:              React, Radix
```

Enforced by dependency-cruiser, package `exports` maps, `cargo tree`/`cargo deny`,
and a forbidden-terms lint. "Core" means the Rust crates and all `@mesh-forge/*`
packages. STL/3MF are generic mesh formats, not domain terms.

## Phase sequence

```
C0 → C1–C3 → C8a (partial freeze) → D0–D2
                                  → C4 → D3
                                  → C5 → D5
                                  → C6 → D6
                                  → C7 → D7
                                  → C8b (depends on C4–C7) → D8
```

C8a freezes the C1–C3 subset ClayField consumes. C8b is the full-stack reuse
proof on `apps/mesh-lab`; it may only require additive changes to the C8a subset.
D8 starts after C8b. For a solo developer, C4–C7 are sequential or interleaved,
not parallel.

## Error codes

- Core/ABI: `MF-<AREA>-<NNN>` (for example `MF-BUF-001`).
- App: `CF-<AREA>-<NNN>`, defined in
  [`../reference/error-codes.md`](../reference/error-codes.md).

Codes are stable; add, never rename. Every code has an i18n message key and a
recovery action.

## Shared documents

| Document | Owner |
|---|---|
| [`../README.md`](../README.md) | docs index |
| [`../security/threat-model.md`](../security/threat-model.md) | security |
| [`../performance/budgets.md`](../performance/budgets.md) | performance |
| [`../data/project-integrity.md`](../data/project-integrity.md) | persistence integrity |
| [`../reference/error-codes.md`](../reference/error-codes.md) | error codes |
| [`../legal/license-policy.md`](../legal/license-policy.md) | licensing |
| [`../accessibility/a11y-plan.md`](../accessibility/a11y-plan.md) | accessibility |
| [`../i18n/i18n-plan.md`](../i18n/i18n-plan.md) | i18n |
| [`../operations/runbooks.md`](../operations/runbooks.md) | operations |
| [`../planning/delivery-and-risks.md`](../planning/delivery-and-risks.md) | delivery |
| [`../adr/`](../adr/) | ADRs |

Core-specific ADRs still go through this shared ADR folder until the core gets
its own `docs/` tree; the core plan's ADR references point here.
