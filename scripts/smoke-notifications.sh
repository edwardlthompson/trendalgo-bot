#!/usr/bin/env bash
# Notification smoke test (H-016).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if command -v uv >/dev/null 2>&1; then
  RUNNER=(uv run python)
else
  RUNNER=(python)
fi

"${RUNNER[@]}" - <<'PY'
from pathlib import Path
import tempfile
from trendalgo.notifications.daily_summary import format_daily_summary
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.sync import sync_kraken_balances

tmp = Path(tempfile.mkdtemp())
store = PortfolioStore(tmp / "portfolio.db")
sync_kraken_balances(store, dry_run=True)
overview = {
    "net_worth_usd": 1500,
    "daily_pnl_usd": 12.5,
    "daily_pnl_pct": 0.008,
    "health_score": 72,
    "allocation": [{"asset": "BTC", "pct": 0.33}],
}
text = format_daily_summary(overview)
assert "Net worth" in text
store.insert_notification("smoke", "Smoke test", text)
assert store.list_notifications()
print("smoke-notifications: PASS")
PY
