#!/usr/bin/env bash
# LTS parity check (H-014 / R-013) — native port validation.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

bash scripts/check_scanner_imports.sh

# Prefer uv (project env); fall back to resolved Python.
if command -v uv >/dev/null 2>&1 || command -v uv.exe >/dev/null 2>&1; then
  UV_BIN="$(command -v uv 2>/dev/null || command -v uv.exe)"
  "$UV_BIN" run --extra dev pytest tests/test_scanner tests/test_uniformity.py tests/test_scanner_listings.py tests/test_lts_vendor tests/test_botd/test_shadow_divergence.py -q --no-cov
else
  # shellcheck source=lib/resolve-python.sh
  . "$(cd "$(dirname "$0")" && pwd)/lib/resolve-python.sh"
  "$PY" -m pytest tests/test_scanner tests/test_uniformity.py tests/test_scanner_listings.py tests/test_lts_vendor tests/test_botd/test_shadow_divergence.py -q --no-cov
fi

MANIFEST="$ROOT/src/trendalgo/scanner/vendor_manifest.json"
if [ ! -f "$MANIFEST" ]; then
  echo "FAIL: missing vendor_manifest.json"
  exit 1
fi
if ! grep -q 'file_vendor' "$MANIFEST"; then
  echo "FAIL: vendor_manifest.json missing file_vendor strategy"
  exit 1
fi
if [ ! -f "$ROOT/examples/web/public/lts-dashboard/index.html" ]; then
  echo "FAIL: missing vendored LTS dashboard"
  exit 1
fi
if [ ! -f "$ROOT/src/trendalgo/lts_vendor/backtesting/runner.py" ]; then
  echo "FAIL: missing vendored LTS backtesting"
  exit 1
fi

ARCH="$(uname -m 2>/dev/null || echo unknown)"
echo "lts-parity-check: arch=$ARCH; TA-Lib indicators stay out of live until amd64 and arm64 captures match (tests/test_lts_vendor/fixtures/talib_arch.json)"
echo "lts-parity-check: PASS (LTS file vendor — H-014 human approval still required)"
