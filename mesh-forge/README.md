# mesh-forge — Reusable Core Plan

Status: reviewed 2026-11-11; owner: Ryan. Docs index: [../docs/README.md](../docs/README.md).
Companion doc: [../clayfield-web/README.md](../clayfield-web/README.md).

mesh-forge is a small, domain-agnostic engine for client-side WebGL2 field/mesh
workbench tools. ClayField is its first consumer. The engine must never import or
reference ClayField/relief concepts.

This plan reflects a contract-level review that found the original split was
separate at the repository level but not at the contract level. The fixes are
folded in below; the most important is the **operation taxonomy** (see §4).

---

## 0. Decisions needed before C0

These are open and block a clean start. Recommended answers are given.

| # | Decision | Recommendation |
|---|---|---|
| MF-1 | Repo topology: one monorepo or two repos? | One monorepo rooted at `clayfield/`: `mesh-forge/` (core), `clayfield-web/` (consumer), `docs/` (shared). Inside `mesh-forge/`, `packages/` for `@mesh-forge/*` and `apps/` for `mesh-lab`; mesh-lab consumes **packed** public packages, not workspace source. |
| MF-2 | Core license + third-party notices | MIT (matches current repo) with its own `LICENSE` and a `NOTICE` listing gl-matrix, zip.js, Radix, React, and Rust crate licenses. |
| MF-3 | Name availability | Verify `@mesh-forge` npm scope, `mesh-forge-core`/`mesh-forge-wasm` on crates.io, and the domain before imports are baked in. |
| MF-4 | Publishing model | Private 0.x tarballs at C8a; public npm only after C8b. Semver policy applies from C8a. |
| MF-5 | Units model | Core buffers are unitless; apps define branded wrappers (see §5). |
| MF-6 | SIMD determinism policy | Golden fixtures run against both SIMD and scalar builds; per-op tolerances documented (see §11). |
| MF-7 | WASM feature baseline | Target SIMD + atomics/shared memory where available; always ship a scalar/non-shared fallback. Feature-detect at init; never require SAB. |

---

## 1. Scope

### In scope
- Field and mesh buffer primitives, validation, transforms.
- A transform pipeline with cancellation, progress, and resource budgets.
- A generic document envelope with nodes, a linear operation stack, and
  command/transaction undo.
- A WebGL2 renderer consuming immutable scene snapshots, with pluggable
  materials, overlays, and pick providers.
- Worker/`SharedArrayBuffer` transport with a transferable fallback.
- An export framework (sink + format registry) with STL and 3MF writers.
- A persistence container (ZIP + manifest + blob store + migration runner) with
  app-supplied schema registration.
- UI primitives (parameter row, numeric field, floating card, split layout,
  viewport host, axis gizmo, dialogs, progress, status).
- A Rust core (`mesh-forge-core`) and a thin ABI crate (`mesh-forge-wasm`).

### Out of scope (defer until a real second consumer)
DCC scene graph/instancing/animation, node-graph editor, dynamic plugin loading,
universal document/material schema, CSG/booleans, PBR, WebGPU backend, generic
sculpt-brush framework, workbench shell, cross-app presets, universal file
format.

### Reuse target
mesh-forge is intended for **field/mesh workbench apps** (relief, embossing,
heightfield sculpting, simple mesh import/transform/export). It is **not** a DCC
engine and does not provide a reusable sculpt engine; those would fork or heavily
extend it.

### Terminology
"Core" means `mesh-forge-core`, `mesh-forge-wasm`, and the `@mesh-forge/*`
packages. ClayField/relief code is the app. STL and 3MF are generic mesh formats,
not domain terms; the forbidden-terms lint does not apply to them.

---

## 2. Repository layout

```
mesh-forge/
├─ packages/
│  ├─ math/                 @mesh-forge/math
│  ├─ buffers/              @mesh-forge/buffers   (Field2D, ImageBuffer, MeshBuffers)
│  ├─ geometry/             @mesh-forge/geometry  (topology, primitives, transforms)
│  ├─ document/             @mesh-forge/document
│  ├─ render/               @mesh-forge/render
│  ├─ viewport-react/       @mesh-forge/viewport-react
│  ├─ export/               @mesh-forge/export
│  ├─ transport/            @mesh-forge/transport
│  ├─ persistence/          @mesh-forge/persistence
│  ├─ wasm-host/            @mesh-forge/wasm-host
│  └─ ui/                   @mesh-forge/ui
├─ crates/
│  ├─ mesh-forge-core/      generic: buffers, ops, pipeline, export sink, ABI descriptors
│  └─ mesh-forge-wasm/      ABI helpers only; no domain ops
├─ apps/
│  └─ mesh-lab/             reuse proof; consumes packed packages
├─ contracts/               C8a artifacts: version.json, api-report.md, *.d.ts
└─ tooling/                 dependency-cruiser, eslint boundaries, CI
```

Note: `Field2D`/`ImageBuffer`/`MeshBuffers` live in `@mesh-forge/buffers`, not in
`@mesh-forge/geometry`, to avoid implying fields are geometry.

---

## 3. Package responsibilities

| Package | Owns | Must not own |
|---|---|---|
| `@mesh-forge/math` | vec/mat/quat, AABB, ray, plane, frustum, transforms, tolerances (wraps gl-matrix) | DOM, GL, React, document, units |
| `@mesh-forge/buffers` | `ImageBuffer`, `Field2D`/`FieldView`, `MeshBuffers`/`MeshView`, shape/stride/metadata, validation, resample | GL, renderer, domain semantics |
| `@mesh-forge/geometry` | indexed topology, attribute layouts, bounds, normals, primitives (grid/box/plane), mesh transforms | GL, renderer, domain solids |
| `@mesh-forge/document` | `DocumentEnvelope`, `Scene`, `Node`, `OperationSpec`, `Command`/`Transaction`/`UndoManager`, dirty tracking, `SchemaRegistry` hooks | Zustand, React, renderer, concrete schemas |
| `@mesh-forge/render` | WebGL2 context, program/buffer/texture caches, camera, `SceneSnapshot` consumer, material/overlay/pick registries, resource lifecycle, context-loss recovery, stats | React, document, UI, domain shaders |
| `@mesh-forge/viewport-react` | canvas host, resize/DPR, input mapping, camera hook, overlay host, axis gizmo | app layout, domain panels |
| `@mesh-forge/export` | `Exporter`/`ExportFormat`/`ExportJob`, low-level `ExportSink`, format registry, validation hooks, STL + 3MF writers | field semantics, app UI |
| `@mesh-forge/transport` | worker pool, typed RPC envelope, request IDs, generation tokens, cancellation, progress, multi-buffer SAB layout + control block, transferable fallback, error codes | domain ops |
| `@mesh-forge/persistence` | ZIP container, `Manifest`, `BlobStore`, content hashing, `MigrationRunner`, `AppSchema`/`SchemaRegistry`, FSA/OPFS/IndexedDB adapters, atomic save, autosave/recovery | concrete document schema |
| `@mesh-forge/wasm-host` | WASM loader, memory views, handle arena + release, ABI handshake/capability manifest, command encode/decode, error mapping | domain op IDs/schemas |
| `@mesh-forge/ui` | Radix-wrapped primitives, tokens, `ParameterRow`, `NumericField`, `FloatingCard` (controlled), `SplitLayout` (slots), `Panel`, `Toolbar`, `Dialog`, `ExportDialog` shell, `Progress`, `StatusBar`, `FileDropZone` | document, renderer, transport, app layout, Zustand |
| `mesh-forge-core` (Rust) | buffers, transform ops, pipeline execution, cancellation/progress/budget, export sink, ABI descriptors, error codes | image codecs, picking semantics, domain exporters/analyzers, relief semantics |
| `mesh-forge-wasm` (Rust) | `#[repr(C)]` POD descriptors, bytemuck helpers, handle ABI, capability aggregation | domain ops |

---

## 4. Contract taxonomy (the key fix)

Do **not** model every capability as `Operation`. Use six capability contracts
(plus `Command` for undo). Authoritative field-level definitions live in
[`contracts/types.ts`](contracts/types.ts); this section is the map, not the
contract.

| Contract | Responsibility | Produces/consumes |
|---|---|---|
| `SourceAdapter` / `Importer` | Turn host bytes or a file into a buffer | → `ImageBuffer`, `Field2D`, or `MeshBuffers`. Image decode is host-side: `createImageBitmap`/`ImageDecoder` for PNG/JPEG/BMP; a dedicated 16-bit TIFF decoder in the app. Core provides the type only. |
| `Operation` | Field→field or mesh→mesh **transform** | buffer → buffer |
| `Query` | Ray pick, sample, measure (not a pipeline stage) | `Ray` → `Hit` / sample |
| `Exporter` | Terminal export job | buffers → bytes via `ExportSink` |
| `Analyzer` | Metrics and warnings | buffers → `Metrics` |
| `Pipeline` | Ordered **transforms only** | buffer chain, cancellable/budgeted |

Supporting types:
- `OperationDescriptor { id, version, paramSchema, inputs: PortType[], outputs: PortType[] }`
- `OperationInstance { descriptorId, params, enabled }`
- `OperationRegistry` — static registration + lookup.
- Port types: `ImageBuffer`, `Field2D`, `MeshBuffers`, `Ray`, `Hit`, `Metrics`.

`OperationSpec` in the document is a linear stack of `OperationInstance`.
`Query`, `Exporter`, and `Analyzer` are invoked explicitly, never placed in the
pipeline stack.

---

## 5. Units and spaces

- Core `Field2D` is **unitless**. It carries shape/stride/metadata only.
- Apps define branded wrappers with explicit spaces:
  - `NormalizedField` — 0..1 normalized image/height source.
  - `Heightfield` — physical millimetres.
- A transform declares the space it accepts and produces. `height.map`
  (normalized → mm) is an app op, not a core op.
- Core must not gain unit semantics; if a future app needs a different space, it
  defines its own wrapper.

---

## 6. Document model

- `DocumentEnvelope { schemaId, schemaVersion, appId, metadata, scene, revision }`.
- `Scene` = flat node list + active node + selection.
- `Node { id, kind, name, visible, locked, transform, parentId?, payload }`.
- Payloads are app-defined and opaque to core (validated by the app's
  `AppSchema`).
- Operations are a **linear stack**, not a DAG.
- Derived data is never persisted; evaluation is cached by
  `(nodeId, contentHash(spec), inputHash, opVersion, schemaVersion, resolution)`.
- Interactive state that is not a batch transform (e.g., sculpt offsets) lives in
  the app payload, not in core as a generic `Layer`. Core provides no document
  `Layer` concept; render-order integers are allowed in `SceneSnapshot`.

---

## 7. Undo/redo contract

- `Command` supports before/after patches **and** blob references.
- `Transaction` groups commands for one user action.
- `UndoManager`: one chronological timeline, bounded by count **and** bytes.
- Coalescing via `mergeKey` + time window (slider edits).
- Large binary edits store dirty-rect patches or blob IDs, never full arrays.
- Domain commands provide `apply`/`invert` (or before/after payloads).
- C2 exit criteria must include a **sculpt-like rectangular-patch command test**,
  not just JSON parameter edits.

---

## 8. Transport and SAB contract

- `RpcEnvelope`, `JobHandle`, `GenerationToken`, `CancelToken`, `Progress`.
- **Multi-buffer SAB set**: `base`, `offsets`, `evaluated`, `display`, plus a
  control block. `display` is the read-only mirror the renderer uploads.
- Control block layout (little-endian, 8-byte aligned): `magic` u32, `version`
  u32, `generation` u32, `cancel` u32, `progress` u32, `dirtyRectCount` u32,
  `dirtyRects` u32[4*16] (max 16 rects, each `x,y,w,h`).
- Single-writer rule: one writer owns `base`/`offsets`/`evaluated`; each buffer
  has its own generation counter. Readers use `Atomics.load` and a double-buffer
  swap (write the inactive buffer, then `Atomics.store` the index); never rely on
  plain payload ordering. A seqlock is valid only with atomic payload accesses,
  which is why the double buffer is the default.
- Dirty-rect reporting for incremental texture upload.
- Transferable-`ArrayBuffer` fallback with the same logical layout when
  `crossOriginIsolated` is false. Cancellation in this mode is
  `worker.terminate()` only — a busy Rust loop cannot poll a message. Budgets
  must be small enough that termination is acceptable, or the job is split into
  short chunks.
- C3 exit criteria: multi-buffer SAB + cancellation + fallback + worker
  crash/restart tests pass.

---

## 9. Renderer plugin contract

- `SceneSnapshot`: immutable draw list (geometry handle, material handle,
  transform, renderOrder integer, pickable flag). Built by
  `@mesh-forge/document`'s `buildSnapshot(scene)`; `render` consumes it read-only
  and never mutates `Scene`.
- Registries: `MaterialRegistry`, `OverlayRegistry`, `PickProviderRegistry`.
- `Material`: program + declared uniform schema + feature flags + depth/state.
- `Overlay`: world/screen-space lines/points, depth-test flag.
- `PickProvider`: receives a ray, returns a `Promise<Hit[]>`; worker-backed queries
  are async. The renderer only supplies the ray.
- R32F texture rules, custom uniform binding, shader composition, resource
  ownership/disposal, and context-loss behavior are documented.
- C4 exit criteria: a **custom domain material, overlay, and pick provider**
  registered from outside the renderer package.

---

## 10. Persistence and versioning

Container (core) is separate from document schema (app):

```
project.zip
  manifest.json        # container version, app id, schema id/version, blobs
  document.json        # app-owned, validated by AppSchema
  blobs/<sha256>.<ext>
```

- `AppSchema`/`SchemaRegistry` registration: `{ schemaId, validate, migrate }`.
- `BlobRef { id, kind, codec, dtype?, shape?, hash, byteLength }`.
- Separate versions: container, `DocumentEnvelope.schemaVersion`, per-op version.
- `MigrationRunner` chains app migrations; unknown future version opens
  read-only.
- Never mutate old files in place; write a new archive. **Atomicity strategy
  (decided):** the archive is content-addressed (`project-<sha256>.zip`); the
  commit point is replacing `manifest.json`, which names the current archive. A
  crash mid-write leaves the old manifest pointing at the old archive. Per host:
  FSA writes the new manifest to a temp file and `move()`s it over the old one
  where `FileSystemFileHandle.move()` exists (Chromium); otherwise the manifest
  lives in IndexedDB and the swap is a single transaction; without either, fall
  back to download. There is no portable atomic rename in FSA/OPFS, so the
  manifest pointer is the only swap point.
- Golden fixtures per schema version.

---

## 11. WASM ABI v1

Define before D0:

- `init(hostApiVersion)` and `describe()` returning a `CapabilityManifest`
  (ABI version, core version, opset version, op list, export formats, limits).
- Capability aggregation across `mesh-forge-wasm` + domain ABI crates.
- Alloc/free + handle arena with explicit `release(handle)`. Handle is `u64`
  (generation in the high 32 bits, index in the low 32) and crosses the JS
  boundary as `BigInt`. Memory growth detaches raw pointers and typed-array views;
  handles stay valid, so callers re-acquire views after growth.
- `invoke(opId, paramsPtr, paramsLen) -> resultHandle`: the single entry point for
  registered domain ops. Result handles are released like any other handle.
- Core error codes: `MF-<AREA>-<NNN>` (e.g. `MF-BUF-001`). App-level codes remain
  `CF-<AREA>-<NNN>` in `../docs/reference/error-codes.md`.
- Bulk buffer descriptors `(ptr, len, dtype, shape)`; caller-allocated preferred.
- Error codes; progress/cancel callback with primitive args only.
- Control messages: small versioned JSON; bulk arrays raw.
- Little-endian; 8-byte alignment; max sizes; version-mismatch behavior.
- No rich objects, strings, or trait objects across the boundary.
- SIMD determinism: golden fixtures run both SIMD and scalar builds; per-op
  tolerances documented.

Four versions: `ABI_VERSION`, `CORE_VERSION`, `OPSET_VERSION`, `OP_VERSION`.
Additive-only within a major; never reuse op IDs.

---

## 12. Dependency rules and guardrails

```
math:        (none)
buffers:     math
geometry:    math, buffers
document:    math, buffers
render:      math, buffers, geometry
viewport-react: math, buffers, geometry, render
export:      math, buffers, geometry
transport:   math, buffers
persistence: math, buffers, document
wasm-host:   mesh-forge-core, mesh-forge-wasm
ui:          React, Radix
```

Enforced in CI:
- `dependency-cruiser` + package `exports` maps; no deep imports.
- CI check: `@mesh-forge/*` never imports `@clayfield/*`.
- Rust `cargo tree` / `cargo deny`: `mesh-forge-core` never depends on a domain
  crate.
- Forbidden-domain-terms lint in core (`relief`, `heightfield`, `sculpt`,
  `fabrication`) except tests/fixtures. STL and 3MF are generic mesh formats, not
  domain terms, so they stay in `@mesh-forge/export`.
- "Core" means `mesh-forge-core`, `mesh-forge-wasm`, and the `@mesh-forge/*`
  packages. The lint applies to all of them.
- Core capability manifest exposes only generic capabilities.
- mesh-lab consumes **packed** public packages in a clean fixture.
- PR checklist: reject domain semantics added to core, or require an ADR.

---

## 13. Phases

| Phase | Deliverable | Exit criteria |
|---|---|---|
| **C0** Foundations | Workspace scaffold, TS project refs, Rust workspace, boundary lint, CI, decisions §0 | Empty packages build; boundaries enforced; MF-1–MF-7 decided |
| **C1** Primitives + taxonomy | `@mesh-forge/math`, `@mesh-forge/buffers`, `@mesh-forge/geometry`, `mesh-forge-core` buffers | Property tests native; wasm build smoke; taxonomy types compile |
| **C2** Document + undo | Envelope, nodes, operation stack, command/transaction/undo, dirty tracking | Apply/invert invariants; sculpt-like rectangular-patch command test; coalescing; bounded history |
| **C3** Transport + WASM host | Worker pool, multi-buffer SAB, ABI v1 handshake, transferable fallback | Multi-buffer + cancellation + fallback + crash/restart + ABI handshake/version-mismatch + memory ownership + bounds + handle release + worker message validation tests |
| **C8a** Partial freeze of consumed contracts | Freeze the C1–C3 subset that ClayField consumes | `contracts/version.json` + `contracts/api-report.md` + `contracts/*.d.ts` checked in; CI drift check; semver policy set; packed 0.x tarball installed into a clean `clayfield-web` fixture and builds |
| **C4** Renderer + viewport | `@mesh-forge/render` + `@mesh-forge/viewport-react` on `SceneSnapshot`, registries | Custom material/overlay/pick-provider test; resource lifecycle; camera math; picking contract; overlay depth; context-loss recovery; frame-time smoke at 512² |
| **C5** Export framework | `@mesh-forge/export`: sink, registry, STL + 3MF writers | Streaming STL; custom exporter test; validation hooks; cancel; binary STL byte-identical to the Python reference writer (fixed triangle order, unit normals, 80-byte header); 3MF opens in lib3mf/slicer (OPC parts `[Content_Types].xml`, `_rels/.rels`, `3D/3dmodel.model`) |
| **C6** Persistence | Container, manifest, blob store, `SchemaRegistry`, migrations | Round-trip; second-app schema fixture; migration chain; atomic save; recovery; unknown-version handling; corrupt/malicious archive rejection; archive limits |
| **C7** UI primitives | `@mesh-forge/ui` + tokens | Controlled `FloatingCard`; `SplitLayout` slots; WCAG 2.2 AA; Storybook/Ladle |
| **C8b** Full-stack reuse proof | `apps/mesh-lab` on packed packages: import, at least two transforms, custom material with a uniform, one sculpt-like stroke, export STL, save/load. Consumes: `math`, `buffers`, `geometry`, `document`, `render`, `viewport-react`, `export`, `transport`, `persistence`, `wasm-host`, `ui`, `mesh-forge-core`, `mesh-forge-wasm`. Depends on C4–C7. | Zero `@clayfield/*` imports in `@mesh-forge/*`; forbidden-terms lint clean; `pnpm pack` clean install; mesh-lab builds with zero core changes; no changes required to the C8a subset; security/fuzz test clean |

**3MF is not streamed:** 3MF is a ZIP container, so its writer needs a
seekable sink and does two passes (or ZIP64 for large meshes); it buffers more
than STL. "Streaming export" applies to STL only.

**C8 split:** C8 is a split gate. C8a is the partial freeze before C4; C8b is the
full-stack reuse proof after C7.

**Sequencing:** C0 → C1–C3 → **C8a** → ClayField D0–D2 → C4–C7 (sequential for
a solo developer; interleaved where independent) → ClayField D3–D7 → C8b →
ClayField D8. C8a is a partial freeze: C8b is the full-stack reuse proof and may
only require additive changes to the C8a subset. C8b depends on C4–C7; it is
independent of ClayField, not of the core.

**Effort:** ~20–26 person-weeks with 20–30% contingency. Per-phase estimates
(planning figures, not commitments):

| Phase | Weeks | Phase | Weeks |
|---|---|---|---|
| C0 | 1–2 | C4 | 2–3 |
| C1 | 2–3 | C5 | 1–2 |
| C2 | 2–3 | C6 | 2–3 |
| C3 | 3–4 | C7 | 2–3 |
| C8a | 1–2 | C8b | 2–3 |

C4–C7 are sequential for a solo developer; "parallel" is not a schedule. The
sum (18–28) brackets the total, so the critical path is checkable: C1–C3 and
C4–C7 are the long poles, and C8b is off the critical path.

---

## 14. Testing

- Rust: unit + property tests for buffers, ops, pipeline invariants (native and
  wasm).
- ABI: command bytes, handshake/version mismatch, memory ownership, bounds,
  handle release.
- Document/undo: apply/invert, coalescing, dirty tracking, bounded history,
  patch correctness.
- Persistence: every schema version fixture, migration chain, unknown version,
  archive limits, atomic save, recovery.
- Transport: cancellation, generation tokens, SAB + fallback, worker
  crash/restart, backpressure.
- Renderer: resource lifecycle, context loss/restore, camera math, picking
  contract, overlay depth; headless WebGL or Playwright screenshots.
- Performance: budgets in CI (frame time, op latency, peak memory, wasm size,
  first-load size).
- Security: malformed archives, decompression bombs, invalid images, worker
  message validation.
- Cross-browser: Chrome/Edge (FSA), Firefox/Safari (fallbacks), COOP/COEP.

---

## 15. Risks

Design-level risk summary. The authoritative register (probability, impact,
trigger) is [`../docs/planning/delivery-and-risks.md`](../docs/planning/delivery-and-risks.md).

| Risk | Symptom | Mitigation |
|---|---|---|
| Over-generalization | Speculative APIs no app uses | Rule of three; keep packages internal; require a second consumer |
| Leaky abstractions | Core knows heightfields; render imports document | Boundary lint; forbidden-terms lint; review |
| Premature plugins | Registry/marketplace before a second app | Static registries; crate/package boundary is the seam |
| WASM boundary bloat | JSON per dab, full-array copies | Bulk buffers, zero-copy views, handle arena, dirty rects |
| Renderer coupling | App state in renderer | `SceneSnapshot` only; registries for domain plugins |
| Undo memory | Full-array snapshots | Patch/blob commands; byte cap |
| SAB races | Stale results, torn reads | Generation tokens; single-writer; seqlock; deterministic tests |
| API freeze too late | ClayField pins/fork | C8a freeze before D0 |
| Repo coupling | Deep imports hide coupling | Packed-package test; separate workspace groups |

---

## 16. Governance and process

Personal-use baseline: keep ceremony low but make decisions durable.

- **ADRs** in `../docs/adr/` for hard-to-reverse choices (taxonomy, units, sculpt
  model, persistence versioning, licensing). Template provided.
- **Commits:** short imperative subject; conventional prefixes encouraged.
  Trunk-based; short-lived branches; direct commits to `main` acceptable for
  small solo changes.
- **Definition of done:** tests/manual check, lint/format, docs updated, no
  unrelated changes (see `../CONTRIBUTING.md`).
- **Versioning:** semver for `mesh-forge-core` and packages from C8a; private 0.x
  tarballs until C8b; public npm only after C8b.
- **Change control:** the C8a-frozen subset is changed only by a versioned,
  additive amendment plus an ADR. Never silently break a consumer.
- **Feature flags:** large/optional features behind a flag so a bad build can be
  disabled without redeploy.
- **Intentionally omitted (add only if public):** CODEOWNERS, CODE_OF_CONDUCT,
  DCO/CLA, RACI, release trains.

## 17. Security and privacy

- Threat model: `../docs/security/threat-model.md`.
- CSP incl. `wasm-unsafe-eval`, COOP/COEP, CORP, HSTS, Permissions-Policy, SRI;
  consider Trusted Types.
- Untrusted input: archives, images, worker messages, ABI commands. Enforce size
  limits and schema validation.
- WASM: minimize `unsafe`, `cargo-geiger`, fuzz decoders, bounds checks.
- Supply chain: committed lockfiles, `cargo audit`/`cargo deny`, dependency
  review, secrets scanning.
- Privacy: no telemetry by default (see `../PRIVACY.md`). Any opt-in reporting must
  redact project content.
- Security tests are required at C3 (worker messages), C6 (archives), and in the
  C8b reuse proof.

## 18. Observability and operations

- Structured logging with levels and redaction; no project content in logs.
- Error boundaries in the React host; renderer and worker errors mapped to codes.
- Diagnostics: version/build hash, WASM ABI/core/opset, WebGL capabilities,
  feature flags, recent error codes. Exportable, redacted support bundle.
- Runbooks: `../docs/operations/runbooks.md` (WASM load, worker crash, context loss,
  quota, update failure).
- SLOs: not required for personal use; define only if hosted publicly.

## 19. Accessibility and i18n

- Target WCAG 2.2 AA for `@mesh-forge/ui` and `@mesh-forge/viewport-react`.
- Keyboard operation for viewport, panels, dialogs, and the floating card;
  visible focus; reduced motion; contrast.
- Canvas exposes model facts as text and ARIA live regions for status/progress.
- i18n-ready: message keys, no hard-coded strings, `Intl` formatting, RTL-safe
  layout. English-only shipping is fine.
- See `../docs/accessibility/a11y-plan.md` and `../docs/i18n/i18n-plan.md`.

## 20. Performance and resource budgets

- Numeric budgets and gates: `../docs/performance/budgets.md`.
- Preflight memory before large allocations; reject over-cap with a clear code.
- Dirty-rect updates, streaming export, backpressure (one in-flight job per
  worker), and resource cleanup (ImageBitmap/object URLs/GL/workers/listeners).
- OOM and context-loss handling are first-class UX, not crashes.
- Benchmarks in CI once the workspace exists; start as warnings, then blocking.

## 21. Data integrity and UX robustness

- Checksums, atomic save, unknown-version read-only, migration runner (see
  `../docs/data/project-integrity.md`).
- Multi-tab writer election (Web Locks; `BroadcastChannel` fallback); second tab
  read-only.
- FSA permission re-prompt and OPFS/download fallback.
- Storage quota handling and `navigator.storage.persist()`.
- Blob dedup and orphan GC.
- Stable error codes (`../docs/reference/error-codes.md`) with user messages.
- Loading/empty/error/offline/read-only states are designed, not improvised.

## 22. Legal and licensing

- Core is MIT; dependency allowlist and GPL/AGPL policy in
  `../docs/legal/license-policy.md`.
- `NOTICE` finalized before any public release.
- Verify npm scope (`@mesh-forge`) and crates.io names before publishing.
- Fonts/icons/assets must have compatible licenses and attribution.
- No export-control/crypto concerns expected; state it if the app ships crypto.

## 23. Delivery and ownership

- Solo, part-time. Estimates are ranges with 20–30% contingency.
- Critical path: C0 → C1–C3 → C8a → consumer D0–D2 → C4–C7 → consumer D3–D7 →
  C8b → consumer D8 (hardening).
- Risk register lives with the consumer plan; core risks are the boundary leaks,
  WASM memory, and API churn.
- `apps/mesh-lab` is the reuse gate: import a real mesh, apply at least two
  transforms, register a custom material with a uniform, run one sculpt-like
  stroke, export STL, save/load. If it needs forks or leaks domain code, fix the
  seams before stabilizing APIs.

## 24. Documentation and developer experience

- Monorepo README with quick start; package/crate READMEs.
- Architecture overview with data-flow diagrams (`../docs/architecture/overview.md`).
- TSDoc + rustdoc; WASM debugging guide (source maps, symbols, panic hooks).
- Docs CI: link check + markdownlint.
- Keep plans and ADRs current when contracts change.
