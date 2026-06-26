#!/usr/bin/env bash
# Apply founder defaults (H-005, H-029, H-021).
# Usage: scripts/apply-founder-defaults.sh [--force]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SRC="$ROOT/config/founder.defaults.json.example"
DST="$ROOT/config/founder.defaults.json"
FORCE="${1:-}"

if [ -f "$DST" ] && [ "$FORCE" != "--force" ]; then
  echo "OK   $DST already exists (use --force to overwrite)"
  exit 0
fi

if [ ! -f "$SRC" ]; then
  echo "FAIL missing $SRC"
  exit 1
fi

mkdir -p "$ROOT/config"
cp "$SRC" "$DST"
echo "OK   copied founder defaults to config/founder.defaults.json"

# Patch .env.example hints if present
ENV_EX="$ROOT/.env.example"
if [ -f "$ENV_EX" ]; then
  python3 - "$ENV_EX" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])
text = p.read_text(encoding="utf-8")
markers = {
    "# TZ=": "TZ=America/Puerto_Rico",
    "# AI_MODE=": "AI_MODE=ollama-first",
    "# DATABASE_URL=": "DATABASE_URL=sqlite:///data/trendalgo.db",
}
for comment, line in markers.items():
    if line not in text and comment not in text:
        text += f"\n{line}\n"
p.write_text(text, encoding="utf-8")
print("OK   .env.example updated with founder default hints")
PY
fi

echo "Run: bash scripts/founder-gate.sh preflight H-005"
