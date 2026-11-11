# Contributing

Status: active. Owner: Ryan. Last reviewed: 2026-11-11.

This repo holds two tracks. Know which one you are touching before you change a file.

| Track | Location | Language | State |
|---|---|---|---|
| Core (reusable) | `mesh-forge/` | TypeScript + Rust | C0 scaffold only; C1 next |
| App (consumer) | `clayfield-web/` | plan only | D0 not started |
| Desktop V2 (history) | repo root `src/`, `legacy-v2/` | Python 3.12 | retained, not the active track |

The desktop app is kept for history and reference. New work goes into the two web
tracks. Do not "fix" the desktop app as part of a web-track change.

## Prerequisites

- Node 22 (`.nvmrc`) and pnpm 12.15.0 (`packageManager` in `mesh-forge/package.json`).
- Rust stable with the components and targets in `mesh-forge/rust-toolchain.toml`
  (`rustfmt`, `clippy`, `wasm32-unknown-unknown`). `rustup` installs these on the
  first `cargo` invocation in the directory.
- Python 3.12 + `uv` only if you are running the desktop app.

## Setup

```bash
cd mesh-forge
pnpm install            # workspace install; commits pnpm-lock.yaml
cargo check --workspace # resolves the Rust workspace and the pinned toolchain
```

## Commands that must pass before you call work done

```bash
cd mesh-forge
pnpm build                              # tsc -b across project references
pnpm lint:boundaries                    # dependency-cruiser edge rules
cargo check --workspace
cargo test --workspace
cargo check -p mesh-forge-wasm --target wasm32-unknown-unknown
pnpm exec tsc --noEmit --strict --target ES2022 --lib ES2022,DOM contracts/types.ts
```

The contract compile is the C1 gate: "types compile" means that command exits 0.
It runs without a project config because no `tsconfig.json` sits beside
`mesh-forge/contracts/types.ts`; if one is added there, pass the project config
instead.

CI runs the same set (`.github/workflows/ci.yml`). A change that passes locally and
fails CI is a change that has not been verified.

## Definition of done

1. Tests or a manual check that exercises the change.
2. Lint and format clean.
3. Docs updated in the same commit — the design lives in each build's `README.md`,
   status in its `TASK-LIST.md`. Do not add a new tracker file.
4. No unrelated changes in the same commit.

## Commits and branches

- Short imperative subject; conventional prefixes encouraged (`feat:`, `fix:`,
  `docs:`, `chore:`).
- Trunk-based. Short-lived branches; direct commits to `main` are acceptable for
  small solo changes.
- A commit that changes a contract names the contract and the version impact.

## Architecture decisions

Hard-to-reverse choices — taxonomy, units, sculpt model, persistence versioning,
licensing — get an ADR in `docs/adr/` from the template there. A decision that only
exists in a chat message is not recorded.

## Change control after C8a

The C8a-frozen subset named in `mesh-forge/contracts/version.json` changes only by a
versioned, additive amendment plus an ADR. Never silently break a consumer.

## Licensing

MIT. Contributions are accepted under the same license. See `LICENSE` and `NOTICE`.
Dependency license rules are in `docs/legal/license-policy.md`.

## Intentionally omitted

CODEOWNERS, CODE_OF_CONDUCT, DCO/CLA, and release trains. Add them only if the
project gains outside contributors.
