# Documentation index

Entry point for all project docs. The desktop app is the active product; the web
builds are a parallel track. The web builds live in their own top-level
directories (`mesh-forge/`, `clayfield-web/`); shared policies live here in
`docs/`.

## Desktop app — start here

The active product. The v3 handoff package lives in `docs-v3-build/`; the desktop
code is `src/`, launched by `main.py`.

| Doc | What it is |
|---|---|
| [../docs-v3-build/README.md](../docs-v3-build/README.md) | Product definition, engineering principles, source-of-truth hierarchy |
| [../docs-v3-build/GUI_LAYOUT.md](../docs-v3-build/GUI_LAYOUT.md) | Authoritative screen, panel, viewport, and interaction spec |
| [../docs-v3-build/VISUAL_DESIGN.md](../docs-v3-build/VISUAL_DESIGN.md) | Visual tokens, component styling, states |
| [../docs-v3-build/IMPLEMENTATION_ROADMAP.md](../docs-v3-build/IMPLEMENTATION_ROADMAP.md) | Phases 0–7, dependencies, risks, acceptance gates |
| [../docs-v3-build/TASK_LIST.md](../docs-v3-build/TASK_LIST.md) | Execution checklist; Phase 0 closed |
| [../docs-v3-build/REPOSITORY_AUDIT.md](../docs-v3-build/REPOSITORY_AUDIT.md) | Phase 0 audit: verified paths, facts, gaps, risks |

## Web track — parallel

A client-side WebGL2 relief/mesh workbench. Built and tested independently of the
desktop product.

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
| [adr/README.md](adr/README.md) | Architecture decision records + template; [ADR-0002](adr/0002-desktop-v3-is-active.md) makes desktop V3 the active product; [ADR-0001](adr/0001-v4-projects-read-only.md) sets web v4 projects read-only and drops presets, crop/resize, terrain noise |
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

## Desktop docs (v2 history)

| Doc | What it covers |
|---|---|
| [development.md](development.md) | Desktop install, lint, test, release |
| [user_guide.md](user_guide.md) | Desktop user guide |
| [print_validation.md](print_validation.md) | Print QA / slicer check |
| [v1_restore.md](v1_restore.md) | v1 restore notes |
| [V2-ACCEPTANCE-REPORT.md](V2-ACCEPTANCE-REPORT.md) | V2 acceptance state |

The desktop v2 roadmap/task lists moved to [`../legacy-v2/`](../legacy-v2/):
`roadmap.md`, `V2-MASTER-PLAN.md`, `V2-BUILD-TASK-LIST.md`,
`V2-MASTER-TASK-LIST.md`, `V2-CANONICAL-ROADMAP.md`. The v3 handoff package in
`docs-v3-build/` supersedes them for current product work.

## Suggested reading order

1. [../docs-v3-build/README.md](../docs-v3-build/README.md)
2. [../docs-v3-build/REPOSITORY_AUDIT.md](../docs-v3-build/REPOSITORY_AUDIT.md)
3. [../docs-v3-build/GUI_LAYOUT.md](../docs-v3-build/GUI_LAYOUT.md)
4. [../docs-v3-build/IMPLEMENTATION_ROADMAP.md](../docs-v3-build/IMPLEMENTATION_ROADMAP.md)
5. Shared docs as each phase needs them (security, performance, data, a11y).
6. Web track docs only when a change is scoped to the web build.
