#!/usr/bin/env bash
# Fail when AVALONIA_PARITY_GAPS AV-G-* IDs drift from BUILD_PLAN rows.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck source=lib/resolve-python.sh
. "$(cd "$(dirname "$0")" && pwd)/lib/resolve-python.sh"
exec "$PY" "$ROOT/scripts/lib/check_avalonia_gap_sync.py" "$ROOT"
