#!/usr/bin/env bash
# Risk mitigation gate — reads docs/risk-catalog.json.
# Usage: scripts/check-risk-mitigations.sh [--strict] [--sprint N] [--ongoing] [--all]
#        scripts/check-risk-mitigations.sh close R-006 --sprint 0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 scripts/check_risk_mitigations.py "$@"
