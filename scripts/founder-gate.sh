#!/usr/bin/env bash
# Founder gate CLI wrapper.
# Usage: scripts/founder-gate.sh status|preflight H-001|approve H-007|backlog H-006|approve-bundle pre-sprint-1|preflight-sprint --sprint 0
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 scripts/founder_gate.py "$@"
