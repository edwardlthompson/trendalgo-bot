#!/usr/bin/env bash
# Portfolio snapshot integrity report (H-026).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DATA="${TRENDALGO_DATA_DIR:-$ROOT/data}/portfolio.db"

if [ ! -f "$DATA" ]; then
  echo "WARN no portfolio.db at $DATA (dry-run may not have synced yet)"
  exit 0
fi

if command -v uv >/dev/null 2>&1; then
  uv run python - <<PY
import os
from pathlib import Path
from trendalgo.portfolio.db import PortfolioStore

db = Path(os.environ.get("TRENDALGO_DATA_DIR", "data")) / "portfolio.db"
store = PortfolioStore(db)
aid = store.get_or_create_account("kraken", "default")
snaps = store.list_snapshots(aid, limit=5)
print(f"OK   recent snapshots: {len(snaps)}")
PY
else
  python - <<PY
import os
from pathlib import Path
from trendalgo.portfolio.db import PortfolioStore

db = Path(os.environ.get("TRENDALGO_DATA_DIR", "data")) / "portfolio.db"
store = PortfolioStore(db)
aid = store.get_or_create_account("kraken", "default")
snaps = store.list_snapshots(aid, limit=5)
print(f"OK   recent snapshots: {len(snaps)}")
PY
fi
