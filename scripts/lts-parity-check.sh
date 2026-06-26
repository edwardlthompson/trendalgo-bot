#!/usr/bin/env bash
# LTS parity check (H-014 / R-013) — native port validation.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

bash scripts/check_scanner_imports.sh

if command -v uv >/dev/null 2>&1; then
  uv run pytest tests/test_scanner -q
else
  python -m pytest tests/test_scanner -q
fi

MANIFEST="$ROOT/src/trendalgo/scanner/vendor_manifest.json"
if [ ! -f "$MANIFEST" ]; then
  echo "FAIL: missing vendor_manifest.json"
  exit 1
fi

echo "lts-parity-check: PASS (native LTS port — H-014 human approval still required)"
