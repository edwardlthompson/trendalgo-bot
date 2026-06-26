#!/usr/bin/env bash
# Fee reconciliation (R-031) — Sprint 10.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/scripts/reconcile-fees.py"
