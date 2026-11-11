# Documentation index

Entry point for all project docs. The two web builds live in their own top-level
directories (`mesh-forge/`, `clayfield-web/`); shared policies live here in
`docs/`.

## Web build — start here

### mesh-forge (reusable core)

| Doc | What it is |
|---|---|
| [../mesh-forge/README.md](../mesh-forge/README.md) | Core design: contracts, phases C0–C8b |
| [../mesh-forge/ROADMAP.md](../mesh-forge/ROADMAP.md) | Core sequence, critical path, milestones |
| [../mesh-forge/TASK-LIST.md](../mesh-forge/TASK-LIST.md) | Core checklist + MF decisions |

### clayfield-web (the app)

| Doc | What it is |
|---|---|
| [../clayfield-web/README.md](../clayfield-web/README.md) | App design: phases D0–D8 |
| [../clayfield-web/ROADMAP.md](../clayfield-web/ROADMAP.md) | App sequence, dependencies, milestones |
| [../clayfield-web/TASK-LIST.md](../clayfield-web/TASK-LIST.md) | App checklist + CF decisions |

Design lives in each build's `README.md`; status lives in its `TASK-LIST.md`.
Do not restate contracts in the task list.

## Shared docs

| Doc | What it covers |
|---|---|
| [architecture/overview.md](architecture/overview.md) | Repo topology, core/app boundary, data flow, package graph, phase sequence |
| [adr/README.md](adr/README.md) | Architecture decision records + template |
| [legal/license-policy.md](legal/license-policy.md) | Dependency licenses, GPL/AGPL, notices, names |
| [quality/test-strategy.md](quality/test-strategy.md) | Test pyramid, parity fixtures, gates |
| [security/threat-model.md](security/threat-model.md) | Threats, CSP/headers, input validation, fuzzing |
| [performance/budgets.md](performance/budgets.md) | Numeric budgets, memory, backpressure |
| [data/project-integrity.md](data/project-integrity.md) | Checksums, recovery, multi-tab, FSA, quota, blobs |
| [accessibility/a11y-plan.md](accessibility/a11y-plan.md) | WCAG 2.2 AA, canvas a11y, keyboard |
| [i18n/i18n-plan.md](i18n/i18n-plan.md) | i18n, formatting, RTL |
| [operations/runbooks.md](operations/runbooks.md) | Failure recovery steps, support bundle |
| [reference/error-codes.md](reference/error-codes.md) | Stable error codes + user messages |
| [planning/delivery-and-risks.md](planning/delivery-and-risks.md) | Effort, critical path, parity matrix, risks |

## Repo-level files

| File | What it is |
|---|---|
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Setup, conventions, definition of done |
| [../legacy-v2/SECURITY.md](../legacy-v2/SECURITY.md) | Disclosure and security scope |
| [../legacy-v2/PRIVACY.md](../legacy-v2/PRIVACY.md) | Local-only / no-telemetry statement |
| [../NOTICE](../NOTICE) | Third-party attribution record |
| [../LICENSE](../LICENSE) | MIT license |

## Existing desktop docs

| Doc | What it covers |
|---|---|
| [development.md](development.md) | Desktop install, lint, test, release |
| [user_guide.md](user_guide.md) | Desktop user guide |
| [print_validation.md](print_validation.md) | Print QA / slicer check |
| [v1_restore.md](v1_restore.md) | v1 restore notes |
| [V2-ACCEPTANCE-REPORT.md](V2-ACCEPTANCE-REPORT.md) | V2 acceptance state |

The desktop roadmap/task lists moved to [`../legacy-v2/`](../legacy-v2/):
`roadmap.md`, `V2-MASTER-PLAN.md`, `V2-BUILD-TASK-LIST.md`,
`V2-MASTER-TASK-LIST.md`, `V2-CANONICAL-ROADMAP.md`. The web builds are the
active track; the desktop app is retained as V2 history.

## Suggested reading order

1. [../mesh-forge/ROADMAP.md](../mesh-forge/ROADMAP.md)
2. [../mesh-forge/README.md](../mesh-forge/README.md) → [../clayfield-web/README.md](../clayfield-web/README.md)
3. [../clayfield-web/TASK-LIST.md](../clayfield-web/TASK-LIST.md)
4. Shared docs as each phase needs them (security, performance, data, a11y).
