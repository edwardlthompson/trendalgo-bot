#!/usr/bin/env python3
"""Fee reconciliation CLI (Sprint 10)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trendalgo.api.state import default_state
from trendalgo.billing.engine import process_journal_trades, reconcile_fees, seed_sample_trades


def main() -> int:
    os.environ.setdefault("TRENDALGO_DATA_DIR", str(ROOT / "data"))
    state = default_state()
    seed_sample_trades(state.trade_journal)
    process_journal_trades(state.billing_store, state.trade_journal, state.risk_manager)
    result = reconcile_fees(state.billing_store, state.trade_journal)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
