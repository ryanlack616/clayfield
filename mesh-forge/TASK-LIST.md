# mesh-forge task list

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked.

Design: [README.md](README.md). Roadmap: [ROADMAP.md](ROADMAP.md). Shared docs:
[../docs/README.md](../docs/README.md). App build:
[../clayfield-web/TASK-LIST.md](../clayfield-web/TASK-LIST.md).

Rule: design changes go in the plan; status changes go here.

---

## Decisions (blocking)

### Before C0
- [ ] MF-1 Repo topology (one monorepo, two workspace groups; packed mesh-lab)
- [ ] MF-2 Core license + own `LICENSE` + `NOTICE`
- [ ] MF-3 Name/namespace availability (`@mesh-forge`, `mesh-forge-core`, crates.io)
- [ ] MF-4 Publishing model (private 0.x tarballs at C8a; public npm after C8b)
- [ ] MF-5 Units model (core unitless; app wrappers)
- [ ] MF-6 SIMD-vs-scalar determinism tolerance policy
- [ ] MF-7 WASM feature baseline (SIMD/atomics optional; scalar fallback required)

---

## Core phases

### C0 — Foundations
Refs: README §0, §2, §12, §13, §16
- [ ] pnpm workspace, TS project refs, Cargo workspace
- [ ] `pnpm-lock.yaml`, `Cargo.lock`, toolchain pinning (`packageManager`, `.nvmrc`, `rust-toolchain.toml`)
- [ ] `tsconfig.base.json` (strict), ESLint/Biome, rustfmt/clippy, `.editorconfig`, pre-commit
- [ ] dependency-cruiser boundaries; forbidden-domain-terms lint in core
- [ ] CI skeleton (`ci.yml`) + branch protection
- [ ] ADR folder + template in use
- [ ] **Exit:** empty packages build; boundaries enforced; MF-1–MF-7 decided

### C1 — Primitives + taxonomy
Refs: README §3, §4, §5, §14
- [ ] `@mesh-forge/math`, `@mesh-forge/buffers`, `@mesh-forge/geometry`
- [ ] `mesh-forge-core` buffers (`Field2D`, `MeshBuffers`, validation, resample)
- [ ] Contract taxonomy types (`SourceAdapter`/`Importer`, `Operation`, `Query`, `Exporter`, `Analyzer`, `Pipeline`)
- [ ] **Exit:** property tests pass native; wasm build smoke; `tsc --noEmit
      --strict` over `contracts/types.ts` exits 0

### C2 — Document + undo
Refs: README §6, §7
- [ ] `DocumentEnvelope`, `Scene`, `Node`, operation stack
- [ ] `Command`/`Transaction`/`UndoManager` with patches + blob refs + coalescing
- [ ] Dirty tracking
- [ ] **Exit:** apply/invert invariants; sculpt-like rectangular-patch command test; coalescing; bounded history

### C3 — Transport + WASM host
Refs: README §8, §11
- [ ] Worker pool, RPC envelope, generation/cancel tokens
- [ ] Multi-buffer SAB set + control block + dirty rects; transferable fallback
- [ ] ABI v1: `init`/`describe`, capability manifest, handle arena, buffer descriptors, error codes
- [ ] **Exit:** multi-buffer + cancellation + fallback + crash/restart + ABI handshake/version-mismatch + memory ownership + bounds + handle release tests

### C8a — Partial freeze of consumed contracts  (blocks D0)
Refs: README §13
- [ ] Freeze the C1–C3 subset ClayField consumes
- [ ] Check in `contracts/version.json`, `contracts/api-report.md`, `contracts/*.d.ts`
- [ ] CI drift check; semver policy set
- [ ] **Exit:** packed 0.x tarball installs into a clean throwaway consumer fixture
      (empty Vite app outside the workspace, `--offline`) and builds. The real
      `clayfield-web` packages arrive in D0; C8a only needs a fixture that proves
      the packed packages install and resolve.

### C4 — Renderer + viewport
Refs: README §9
- [ ] `@mesh-forge/render`: context, camera, resources, `SceneSnapshot`
- [ ] Material/overlay/pick-provider registries
- [ ] `@mesh-forge/viewport-react`: canvas host, input, camera hook, gizmo
- [ ] **Exit:** custom material/overlay/pick-provider test; resource lifecycle; camera math; picking contract; overlay depth; context-loss recovery; frame-time smoke at 512²

### C5 — Export framework
Refs: README §3 (Exporter), §13
- [ ] `Exporter`/`ExportFormat`/`ExportJob`, low-level `ExportSink`, registry
- [ ] STL + 3MF writers; validation hooks
- [ ] **Exit:** streaming STL; custom exporter test; validation hooks; cancel; binary STL byte-identical to reference writer; 3MF opens in lib3mf/slicer (OPC parts present)

### C6 — Persistence
Refs: README §10
- [ ] Container, `Manifest`, `BlobStore`, content hashing
- [ ] `AppSchema`/`SchemaRegistry`, `MigrationRunner`
- [ ] FSA/OPFS/IndexedDB adapters; atomic save; autosave/recovery
- [ ] **Exit:** round-trip; second-app schema fixture; migration chain; atomic save; recovery; unknown-version handling; corrupt/malicious archive rejection; archive limits

### C7 — UI primitives
Refs: README §3, §19
- [ ] `@mesh-forge/ui`: tokens, `ParameterRow`, `NumericField`, controlled `FloatingCard`, `SplitLayout` slots, dialogs, progress, status
- [ ] a11y baseline; Storybook/Ladle
- [ ] **Exit:** controlled card; `SplitLayout` slots; WCAG 2.2 AA keyboard/a11y pass; Storybook/Ladle

### C8b — Full-stack reuse proof  (depends on C4–C7)
Refs: README §13, §12
- [ ] `apps/mesh-lab` on **packed** packages: mesh import, at least two transforms, custom material with a uniform, one sculpt-like stroke, export STL, save/load
- [ ] Consume: `math`, `buffers`, `geometry`, `document`, `render`, `viewport-react`, `export`, `transport`, `persistence`, `wasm-host`, `ui`, `mesh-forge-core`, `mesh-forge-wasm`
- [ ] `pnpm pack` + clean-fixture install test
- [ ] **Exit:** zero `@clayfield/*` imports in `@mesh-forge/*`; forbidden-terms lint clean; mesh-lab builds with zero core changes; no changes required to the C8a subset; security/fuzz test clean

---

## Cross-cutting gates (apply per phase)

- [ ] Tests: unit/property/golden/contract/E2E/visual
- [ ] Lint/format/typecheck
- [ ] Security: input limits, headers, dependency audit
- [ ] Performance: budgets measured, no regressions
- [ ] Accessibility: keyboard + axe + manual pass
- [ ] Docs/plan/ADR updated

## Done log

- (append completed phases with date and notable decisions)
