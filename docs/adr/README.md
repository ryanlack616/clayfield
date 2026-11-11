# Architecture Decision Records

Short records of durable decisions. One file per decision, numbered
sequentially. Write one when a choice is hard to reverse, affects more than one
package, or would otherwise be re-litigated later.

Not every decision needs an ADR. Use judgement; for a personal project, a few
good ones beat a pile of ceremony.

## Format

Copy [0000-template.md](0000-template.md) to `NNNN-short-title.md`.

Status values: `proposed`, `accepted`, `superseded by NNNN`, `rejected`.

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-v4-projects-read-only.md) | v4 projects are read-only; web v1 drops presets, crop/resize, and terrain noise | accepted 2026-11-11 |
| [0002](0002-desktop-v3-is-active.md) | Desktop V3 is the active product; web builds are a parallel track | accepted 2026-11-11 |

Add entries here as ADRs are written.

---

Index: [docs/README.md](../README.md).
