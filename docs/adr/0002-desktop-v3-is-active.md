# 0002. Desktop V3 is the active product; web builds are a parallel track

- Status: accepted
- Date: 2026-11-11
- Deciders: Ryan

## Context

The repo carried two plans. The root README called the web builds active and the
desktop app "legacy", while the desktop app is in fact the shipping product and
the `docs-v3-build/` package redesigns it. The Phase 0 audit confirmed the
desktop app is healthy (361 tests pass, 75 modules import clean) and that the v3
UI is a different architecture from the current splitter shell, which opens at
1309×820 (the `resize(1280, 820)` request is below its 1309×440 minimum).

Ryan holds a backup of the full repo, so committing to one direction carries no
data-loss risk.

## Decision

Desktop V3 is the active product. The web builds (`mesh-forge/`,
`clayfield-web/`) remain a parallel track: not cancelled, not the active
direction, and not the place new product work goes by default.

Concretely:

- Product work goes into `src/`, `main.py`, and `docs-v3-build/`.
- The web track keeps its own docs, gate, and task lists; changes there are
  explicitly scoped web changes.
- ADR-0001 applies to the web track only.
- Desktop V2 docs stay in `legacy-v2/` as history; the v3 package supersedes them
  for current work.

## Consequences

Easier: one product to build and test; the desktop pipeline, mask data model,
export path, and undo ledger are already real and tested; the web track stays
available as a fallback.

Harder: the desktop app's UI must be rebuilt (docks, tabs, persistent viewport,
mask editor); the web track's C0/C1 work is paused and will drift.

Giving up: the "web first" framing and the assumption that desktop is legacy. The
web track's ADR-0001 scope decisions remain valid for that track but do not bind
the desktop app.

## Alternatives considered

- **Web active.** Rejected: the desktop app is the shipping product and the v3
  package targets it. Making web active would strand the product being redesigned.
- **Both active.** Rejected: two products, one maintainer, and the web track has no
  user-facing app yet.
- **Leave the conflict unrecorded.** Rejected: the docs already contradicted each
  other; a future session would re-litigate it.
