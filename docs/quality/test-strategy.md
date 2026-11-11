# Test strategy

Personal-scale but rigorous where it matters: numerical correctness, export
integrity, persistence, and the engine/app boundary.

## Pyramid

1. **Unit** — pure functions (image ops, terrain mapping, sculpt kernels, mesh
   topology, export writers). Fast, no GPU.
2. **Property** — invariants (field shape/finite, mesh watertight/positive
   volume, undo apply→invert round-trips). Use `proptest` (Rust) and `fast-check`
   (TS) when the web work starts.
3. **Golden/parity** — fixtures generated from the Python app; see below.
4. **Contract** — ABI command bytes, capability manifest/version mismatch,
   worker RPC envelopes, persistence schema versions.
5. **Integration/E2E** — upload → adjust → sculpt → export; Playwright for web.
6. **Visual regression** — viewport screenshots with fixed cameras/fixtures.
7. **Performance** — frame time, sculpt latency, export time, peak memory.
8. **Security** — malformed archives/images, worker message validation, fuzz.
9. **Accessibility** — axe + manual screen-reader matrix.

## Parity fixtures

- Generated from the Python app with a **pinned environment** (record Python and
  dependency versions).
- Store small fixtures in-repo; large ones in Git LFS or an artifact store.
- Cover: grayscale/channel order, levels/curve rounding (banker's rounding),
  blur (reflect-101, kernel size), sharpen (9×9 σ1.0), threshold, adjustment
  order, height mapping, picking, matrix convention.
- Run against **both SIMD and scalar** WASM builds; record per-op tolerances.
- Fixtures are owned and reviewed; regeneration is a deliberate, documented step.

## Gates (personal)

- `pytest` + `ruff` for the desktop app.
- Once web exists: typecheck, lint, unit/property tests, contract tests, a small
  E2E smoke, and parity fixtures in CI.
- Performance and security gates can start as non-blocking warnings, then become
  blocking once baselines are stable.

## Flaky tests

Quarantine a flaky test with an issue note rather than retrying forever. Prefer
deterministic fixtures and fixed seeds.

---

Part of the web build docs. Index: [docs/README.md](../README.md).
