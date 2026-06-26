#!/usr/bin/env bash
# Hosting eligibility Oracle/Hetzner (H-004 / R-016).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$ROOT/docs/DEPLOYMENT.md" ]; then
  echo "OK   DEPLOYMENT.md present"
  exit 0
fi
echo "SCHEDULED — create docs/DEPLOYMENT.md"
exit 2
