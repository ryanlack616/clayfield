# Contributing

This is primarily a personal project, so keep process light. The goal is that
future-you (or a collaborator) can pick it up quickly and trust the results.

Docs index: [docs/README.md](docs/README.md).

## Current repo (Python desktop app)

```sh
python -m venv .venv
.venv/bin/pip install -e '.[dev,test]'
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

Optional checks are documented in [docs/development.md](docs/development.md).

## Planned web work

The web rewrite is split into two builds:

- [mesh-forge/README.md](mesh-forge/README.md) — reusable core
  ([roadmap](mesh-forge/ROADMAP.md), [task list](mesh-forge/TASK-LIST.md))
- [clayfield-web/README.md](clayfield-web/README.md) — ClayField on the core
  ([roadmap](clayfield-web/ROADMAP.md), [task list](clayfield-web/TASK-LIST.md))

When that work starts, the monorepo baseline (toolchain pinning, lockfiles,
lint/format config, CI) is defined in mesh-forge/README.md §16 and the
"project hygiene" checklist. Do not begin C0 until that baseline exists.

## Conventions

- **Commits:** short imperative subject; one logical change per commit.
  Conventional-commit prefixes (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`,
  `test:`) are encouraged but not enforced.
- **Branches:** short-lived; prefer trunk-based development. Solo work may commit
  directly to `main` for small changes.
- **Formatting/lint:** `ruff` is the gate for Python. Do not hand-format around it.
- **Docs:** update the relevant plan or guide when behavior or architecture
  changes. Record durable decisions as ADRs in [docs/adr](docs/adr).
- **No secrets** in the repo. No telemetry or network calls without an explicit
  decision and a privacy note.

## Definition of done (personal scale)

- [ ] Change works and is covered by a test or a manual check noted in the PR.
- [ ] `pytest` and `ruff` pass (or the web equivalents once they exist).
- [ ] Docs/plan updated if behavior or design changed.
- [ ] No unrelated changes bundled in.

## Review

Solo project: self-review the diff before committing. If a change is risky
(export format, persistence, licensing, security), write an ADR first.

Enterprise-only artifacts (CODEOWNERS, CODE_OF_CONDUCT, DCO/CLA, release trains)
are intentionally omitted. Add them if the project gains outside contributors or
is published.
