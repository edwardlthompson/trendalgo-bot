#!/usr/bin/env bash
# Close a risk after verification PASS.
# Usage: scripts/close-risk.sh R-006 --sprint 0 [--note "..."] [--force]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
RID="$1"; shift
exec python3 scripts/check_risk_mitigations.py close "$RID" "$@"
