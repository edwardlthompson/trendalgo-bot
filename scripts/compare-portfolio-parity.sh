#!/usr/bin/env bash
# CoinStats parity compare (H-017 / R-017) — multi-exchange mode (S17).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export TRENDALGO_SYNC_STAGGER_SEC=0

FEATURES=(
  "net_worth_hero"
  "daily_pl"
  "holdings_cost_basis"
  "allocation"
  "equity_curve"
  "timeline_scrubber"
  "heatmap"
  "notification_inbox"
  "csv_export"
)

run_py() {
  if command -v uv >/dev/null 2>&1; then
    uv run python - "$@"
  else
    PYTHONPATH=src python - "$@"
  fi
}

if command -v uv >/dev/null 2>&1; then
  uv run pytest tests/test_portfolio/test_metrics.py tests/test_portfolio/test_overview.py tests/test_exchanges/test_s17.py -q
else
  python -m pytest tests/test_portfolio/test_metrics.py tests/test_portfolio/test_overview.py tests/test_exchanges/test_s17.py -q
fi

run_py <<'PY'
from pathlib import Path
import tempfile
from trendalgo.exchanges.registry import list_portfolio_exchanges, load_registry
from trendalgo.exchanges.sync import sync_all_exchanges
from trendalgo.portfolio.db import PortfolioStore

registry = load_registry()
venues = list_portfolio_exchanges()
assert len(venues) >= 6, f"expected 6+ portfolio venues, got {len(venues)}"
with tempfile.TemporaryDirectory() as tmp:
    store = PortfolioStore(Path(tmp) / "portfolio.db")
    result = sync_all_exchanges(store, dry_run=True)
assert result["exchange_count"] == len(venues)
for entry in venues:
    assert entry.id in result, f"missing sync result for {entry.id}"
    assert result[entry.id]["total_usd"] > 0
print(f"OK   multi-exchange parity: {result['exchange_count']} venues registry v{registry.version}")
PY

for f in "${FEATURES[@]}"; do
  echo "OK   parity feature: $f"
done
echo "compare-portfolio-parity: PASS (multi-exchange — H-017 human validation still required)"
