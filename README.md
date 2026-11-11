# ClayField

Two tracks in one repo:

- **Web builds (active).** A client-side WebGL2 relief/mesh workbench, split into a
  reusable core and the app on top of it.
  - [`mesh-forge/`](mesh-forge/README.md) — domain-agnostic core. Phases C0–C8b.
  - [`clayfield-web/`](clayfield-web/README.md) — the app. Phases D0–D8.
- **Desktop V2 (legacy).** The PySide6/NumPy desktop app and its planning docs,
  moved to [`legacy-v2/`](legacy-v2/). Retained as history and as the parity
  reference for the web builds.

Start at the documentation index: [`docs/README.md`](docs/README.md).

## Layout

```
clayfield/
├─ mesh-forge/        core workspace (pnpm + Cargo)
│  ├─ packages/       11 @mesh-forge/* packages
│  ├─ crates/         mesh-forge-core, mesh-forge-wasm
│  ├─ apps/mesh-lab/  reuse proof
│  └─ contracts/      frozen C8a artifacts (types.ts, abi-v1.md, version.json)
├─ clayfield-web/     the app plan + packages
├─ docs/              shared policies (security, perf, data, a11y, i18n, legal)
├─ legacy-v2/         desktop V2 app docs
└─ src/, main.py      desktop V2 code (still the shipping product)
```

## Quick checks

```sh
cd mesh-forge
pnpm install && pnpm build && pnpm lint:boundaries
cargo check --workspace && cargo test --workspace
pnpm exec tsc --noEmit --strict --target ES2022 --lib ES2022,DOM contracts/types.ts
```

## License

MIT. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
