#!/usr/bin/env bash
# The gate. Runs the same checks as .github/workflows/ci.yml without needing
# GitHub Actions — which matters because Actions is blocked on this account.
#
# Usage:
#   scripts/check.sh          full run (CI equivalent)
#   scripts/check.sh --fast   lint + typecheck + boundaries only (pre-commit)
#
# Exit 0 means every gate passed. Any failure prints the step and exits 1.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MF="$ROOT/mesh-forge"
FAST=0
[ "${1:-}" = "--fast" ] && FAST=1

fail() { printf '\n\033[31m✗ %s\033[0m\n' "$1" >&2; exit 1; }
step() { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; }

cd "$MF" || fail "mesh-forge/ not found"

step "biome: lint + format"
pnpm exec biome check . || fail "biome check"

step "tsc -b: build (empty packages must compile)"
pnpm build || fail "tsc -b"

step "tsc: contract types compile"
pnpm exec tsc --noEmit --strict --target ES2022 --lib ES2022,DOM contracts/types.ts \
  || fail "contract types do not compile"

step "dependency-cruiser: boundary lint"
pnpm lint:boundaries || fail "boundary violation"

step "forbidden-domain-terms lint (core only)"
if grep -rniE '\b(relief|heightfield|sculpt|fabrication)\b' \
     --include='*.ts' --include='*.rs' packages crates 2>/dev/null \
     | grep -v '/tests/' | grep -v '/fixtures/'; then
  fail "domain term found in core"
fi

step "cargo check --workspace"
cargo check --workspace || fail "cargo check"

step "cargo check --target wasm32-unknown-unknown"
cargo check -p mesh-forge-wasm --target wasm32-unknown-unknown || fail "wasm32 check"

if [ "$FAST" -eq 0 ]; then
  step "cargo test --workspace"
  cargo test --workspace || fail "cargo test"

  step "pnpm -r pack (package contents)"
  rm -rf /tmp/mf-pack
  pnpm -r pack --pack-destination /tmp/mf-pack >/dev/null || fail "pack check"

  step "docs: relative link integrity"
  ( cd "$ROOT" && python3 scripts/check_md_links.py . ) || fail "broken markdown link"
fi

printf '\n\033[32m✓ all checks passed\033[0m\n'
