# Contributing

Status: active. Owner: Ryan. Last reviewed: 2026-11-11.

This repo holds an active product and a parallel track. Know which one you are
touching before you change a file.

| Track | Location | Language | State |
|---|---|---|---|
| Desktop V3 (active) | repo root `src/`, `main.py`, `docs-v3-build/` | Python 3.12+ | active product; Phase 0 audit done |
| Core (parallel) | `mesh-forge/` | TypeScript + Rust | C0 scaffold only; C1 next |
| App (parallel) | `clayfield-web/` | plan only | D0 not started |
| Desktop V2 (history) | `legacy-v2/` | Python 3.12 | retained as history |

New product work goes into the desktop app unless a change is explicitly scoped to
the web track. Do not "fix" the desktop app as part of a web-track change, and do
not rewrite working pipeline code to match a UI spec.

## Prerequisites

Desktop app (active product):

- Python 3.12+ and `uv`. The project venv is `.venv` (Python 3.13); the system
  Python is 3.14. Run the desktop tests with `env -u PYTHONPATH .venv/bin/python -m
  pytest -q`.

Web track (parallel):

- Node 22 (`.nvmrc`) and pnpm 12.15.0 (`packageManager` in `mesh-forge/package.json`).
- Rust stable with the components and targets in `mesh-forge/rust-toolchain.toml`
  (`rustfmt`, `clippy`, `wasm32-unknown-unknown`). `rustup` installs these on the
  first `cargo` invocation in the directory.

## Setup

Desktop app:

```bash
python -m venv .venv                  # or reuse the existing .venv
.venv/bin/python -m pip install -e ".[test]"
env -u PYTHONPATH .venv/bin/python -m pytest -q
```

Web track:

```bash
git config core.hooksPath .githooks   # enables the pre-commit gate
cd mesh-forge
pnpm install                          # workspace install; commits pnpm-lock.yaml
cargo check --workspace               # resolves the Rust workspace and pinned toolchain
```

`pnpm install` runs the workspace's `prepare` script, which sets `core.hooksPath`
for you; the explicit `git config` line is the fallback if you skip the install.
The hook runs the markdown link check on every commit and the heavier gate only
when a covered path is staged. Bypass it deliberately with `git commit --no-verify`.

## Commands that must pass before you call work done

Desktop app:

```sh
env -u PYTHONPATH .venv/bin/python -m pytest -q   # 361 tests
.venv/bin/python main.py --self-test              # geometry self-test, no display
```

Web track:

```bash
scripts/check.sh          # the full gate — the same one CI runs
scripts/check.sh --fast   # lint, typecheck, boundaries, rust check only
```

`scripts/check.sh` is the single definition of the gate: biome, the TypeScript
build, the contract compile, the boundary lint, the forbidden-terms lint, cargo
check and test, the wasm32 smoke, the package pack check, and the markdown link
sweep. `.github/workflows/ci.yml` calls that script rather than restating the
steps, so a local pass and a CI pass cannot disagree. Edit the script, not the
workflow.

Per-step commands, when you want one:

```bash
cd mesh-forge
pnpm lint            # biome check: lint + format
pnpm lint:fix        # biome check --write
pnpm build           # tsc -b across project references
pnpm lint:boundaries # dependency-cruiser edge rules
pnpm exec tsc --noEmit --strict --target ES2022 --lib ES2022,DOM contracts/types.ts
cargo check --workspace
cargo test --workspace
cargo check -p mesh-forge-wasm --target wasm32-unknown-unknown
```

The contract compile is the C1 gate: "types compile" means that command exits 0.
It runs without a project config because no `tsconfig.json` sits beside
`mesh-forge/contracts/types.ts`; if one is added there, pass the project config
instead.

CI runs the same set (`.github/workflows/ci.yml`), which calls `scripts/check.sh`
rather than restating the steps. A change that passes locally and fails CI is a
change that has not been verified.

GitHub Actions cannot start jobs on this account while it is billing-locked. To
run the workflow itself without GitHub, install `act` and run it from the repo
root:

```bash
act push --rm        # executes .github/workflows/ci.yml in Docker
```

## Definition of done

1. Tests or a manual check that exercises the change.
2. Desktop app: `env -u PYTHONPATH .venv/bin/python -m pytest -q` passes. Web
   track: `scripts/check.sh --fast` passes — lint, format, typecheck, boundaries.
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

## Change control after C8a (web track)

The C8a-frozen subset named in `mesh-forge/contracts/version.json` changes only by a
versioned, additive amendment plus an ADR. Never silently break a consumer.

## Licensing

MIT. Contributions are accepted under the same license. See `LICENSE` and `NOTICE`.
Dependency license rules are in `docs/legal/license-policy.md`.

## Intentionally omitted

CODEOWNERS, CODE_OF_CONDUCT, DCO/CLA, and release trains. Add them only if the
project gains outside contributors.
