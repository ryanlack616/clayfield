# 0001. v4 projects are read-only; web v1 drops presets, crop/resize, and terrain noise

- Status: accepted
- Date: 2026-11-11
- Deciders: Ryan

## Context

The desktop app (v4) stores settings the web v1 plan drops. The open question
was what happens to a v4 project that uses them. Three candidate features sit on
different layers:

- **Presets** — `src/clayfield/app/presets.py` writes
  `{"version": 1, "parameters": {...}}` over the whole `PARAMETERS` snapshot.
  The v4 list includes `composition_settings`, `secondary_source_descriptor`,
  `mask_source_descriptor`, `crop_margins`, `image_resize`, and all five
  `noise_*` fields. The loader rejects unknown fields, so a v1 loader needs its
  own allowlist.
- **Crop/resize** — `src/clayfield/image/geometry.py:52`
  `apply_image_geometry(source, margins, resize)` runs *before* the PROCESS
  stack and changes the pixel grid. v4 stores it in `image_geometry` at
  `project_io.py:519`. It is a source-geometry step, not a PROCESS operation.
- **Terrain noise** — `src/clayfield/terrain/heightfield.py:148` uses
  `np.random.default_rng(seed)` (PCG64) and adds noise to the heightfield; v4
  stores `noise_amplitude/frequency/seed/octaves/persistence` in the `terrain`
  block (`project_io.py:528–532`). It is an additive modifier, not a generator
  source, so the "no procedural generators" scope line does not cover it.

The app plan's "no silent data loss" rule
([`clayfield-web/README.md` §8 and §19](../../clayfield-web/README.md)) rules
out a lossy migration. CF-2 (the v4 compatibility policy) is the gate: CF-6 and
CF-3 are downstream of it, and the presets half of CF-1 is downstream of both.

## Decision

1. **v4 projects open read-only.** A v4 project opens in the web app with a
   banner naming the unsupported features. No lossy migration and no silent
   rewrite. The user can save a new v5 project only when the project uses none
   of the dropped features.
2. **Web v1 drops crop/resize** (CF-6). A v4 project using `image_geometry`
   opens read-only.
3. **Web v1 drops terrain noise** (CF-3). A v4 project with
   `noise_amplitude > 0` opens read-only.
4. **Web v1 drops presets** (CF-1). Keep recent projects, light/dark themes,
   cross-section, and export preview. A v1 preset loader, if added later, needs
   a v1 allowlist and must reject unknown fields.

v4 projects that use none of the dropped features migrate normally; CF-2 still
governs those.

## Consequences

- **Easier:** D1's PROCESS stack is locked without crop/resize or noise. No
  PCG64 port, no preset schema, no `image_geometry` round-trip, and smaller
  parity fixtures.
- **Harder:** v4 users who relied on presets or noise lose those workflows in
  the web app. They keep the desktop app (not sunset until parity) and the v4
  file (read-only).
- **Giving up:** v4 presets are not importable; a v4 project using crop/resize
  or noise is not editable. The v1 document schema is a strict subset of v4's.
- **Reversibility:** presets and noise are additive later — a preset format is a
  new document type and noise is a new op with a deterministic RNG. Crop/resize
  is a source-geometry step, so adding it later changes the document schema, not
  just the op set. That is the expensive one to defer.

## Alternatives considered

- **Migrate everything.** Rejected: requires a PCG64 port, a preset format, and
  an `image_geometry` stage in v1 — all deliberately cut from the v1 scope.
- **Reject v4 projects outright.** Rejected: violates "no silent data loss" and
  loses read-only access to old work.
- **Keep crop/resize, drop noise and presets.** Considered: crop/resize is the
  only one that changes the source pixel grid, so it is the most expensive to add
  later. But keeping it only pays off if v4 projects must be *editable*, which
  read-only already solves.
