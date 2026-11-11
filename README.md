# ClayField

**Desktop V3 is the active product.** The web builds remain a parallel track, not
the active direction.

## Active product — desktop V3

The PySide6/NumPy desktop application: one image → relief → inspect → mask →
selective cleanup → STL/3MF. The v3 redesign lives in
[`docs-v3-build/`](docs-v3-build/); its Phase 0 audit is
[`docs-v3-build/REPOSITORY_AUDIT.md`](docs-v3-build/REPOSITORY_AUDIT.md).

```sh
python main.py --version       # ClayField 2.0.0
python main.py --self-test     # geometry self-test, no display
python -m pytest -q            # 361 tests
```

The desktop code is `src/`, launched by `main.py` → `clayfield.app.application:run`.
The v3 handoff package asks for a read-only audit first; that audit is done. The
current window is a 1280×820 `QSplitter` shell; v3 specifies a docked three-column
shell with five workspace tabs and a painted weighted mask. Phase 1 is a shell
rebuild, not a restyle.

## Parallel track — web builds

A client-side WebGL2 relief/mesh workbench, split into a reusable core and the
app on top of it. Built and tested independently of the desktop product.

- [`mesh-forge/`](mesh-forge/README.md) — domain-agnostic core. Phases C0–C8b.
- [`clayfield-web/`](clayfield-web/README.md) — the app. Phases D0–D8.

Start at the documentation index: [`docs/README.md`](docs/README.md).

## Layout

```
clayfield/
├─ docs-v3-build/      desktop V3 handoff package (active)
├─ src/, main.py       desktop V3 code (active product)
├─ docs/               shared policies (security, perf, data, a11y, i18n, legal)
├─ mesh-forge/         core workspace (pnpm + Cargo) — parallel track
│  ├─ packages/        11 @mesh-forge/* packages
│  ├─ crates/          mesh-forge-core, mesh-forge-wasm
│  ├─ apps/mesh-lab/   reuse proof
│  └─ contracts/       frozen C8a artifacts (types.ts, abi-v1.md, version.json)
├─ clayfield-web/      the app plan + packages — parallel track
├─ legacy-v2/          desktop V2 history docs
├─ tests/              desktop test suite (361 tests)
├─ scripts/            gates and helper scripts
└─ pyproject.toml      desktop package definition
```

## Web quick checks

```sh
cd mesh-forge
pnpm install && pnpm build && pnpm lint:boundaries
cargo check --workspace && cargo test --workspace
pnpm exec tsc --noEmit --strict --target ES2022 --lib ES2022,DOM contracts/types.ts
```

## License

MIT. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
