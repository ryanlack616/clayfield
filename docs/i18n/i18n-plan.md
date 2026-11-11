# Internationalization plan

Start English-only, but structure strings so translation is not a rewrite later.

## Principles

- No hard-coded user-facing strings in components; use message keys.
- Errors use stable codes + message keys (see
  [docs/reference/error-codes.md](../reference/error-codes.md)).
- Format numbers, units, and dates via `Intl`, not string concatenation.
- Units: millimetres only in v1; label them and format consistently.

## Setup (when web work starts)

- Pick a small i18n library (e.g., `@formatjs/intl` or `i18next`).
- Message catalogs per locale; extract keys in CI.
- Keep domain terms in a glossary ([docs/reference/glossary.md] if added).
- Avoid layout assumptions that break with longer translations; use flex/grid.
- Plan for RTL (logical CSS properties) even if no RTL locale ships initially.

## Not in scope for v1

- Multiple locales, RTL shipping, translated documentation.
- Localized presets or file formats (keep format stable and locale-neutral).

---

Part of the web build docs. Index: [docs/README.md](../README.md).
