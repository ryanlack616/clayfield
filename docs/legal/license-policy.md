# License policy

This project is MIT (see [LICENSE](../../LICENSE)). The planned web core
(mesh-forge) will also be MIT so it can be reused; when that crate/package is
created it needs its own `LICENSE` file and license field.

## Rules

- Prefer permissive licenses: MIT, BSD-2/3, Apache-2.0, ISC, Zlib.
- **LGPL** is acceptable only for dynamically linked desktop libraries (e.g.,
  PySide6/Qt) with distribution obligations understood. Do not statically link
  LGPL code into a distributed binary.
- **GPL/AGPL** code must not be linked or bundled unless the whole project adopts
  that license. Verify `fractalnow` before any bundling; it is dropped from the
  web scope.
- Every dependency must be recorded in [NOTICE](../../NOTICE) before a public
  release.
- Run a license scan in CI once the web workspace exists:
  - Rust: `cargo deny check licenses` with `deny.toml` allowlist.
  - JS: a license-checker / `pnpm licenses` step.

## Allowlist (starting point)

MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, ISC, Zlib, 0BSD, CC0-1.0,
Unicode-DFS-2016, MPL-2.0 (file-level), LGPL-3.0 (desktop dynamic only).

## Trademark / name

Before publishing: confirm `ClayField` and `mesh-forge` are not trademarks you
would infringe, and that the npm scope (`@mesh-forge`) and crates.io names are
available. This is a personal project, so a light check is enough; do it before
publishing under those names.

## Assets

Fonts, icons, and sample images must have compatible licenses and be attributed.
Avoid bundling assets with unclear provenance.

---

Part of the web build docs. Index: [docs/README.md](../README.md).
