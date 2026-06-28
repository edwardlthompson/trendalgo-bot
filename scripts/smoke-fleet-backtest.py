#!/usr/bin/env python3
"""Smoke test TA fleet backtest — verbose progress, top 10, buy & hold, optimize pass."""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))

os.environ.setdefault("TRENDALGO_MARKET_SOURCE", "synthetic")


def main() -> int:
    data_dir = Path(tempfile.mkdtemp(prefix="fleet-smoke-"))
    os.environ["TRENDALGO_DATA_DIR"] = str(data_dir)

    import trendalgo.backtest.fleet_runner as fr
    import trendalgo.backtest.ta_fleet as ta_fleet

    fr.TRADINGVIEW_INTERVALS = ("60",)
    ta_fleet.all_strategies = lambda: ("RSI", "MACD", "ROC")
    fr.all_strategies = ta_fleet.all_strategies

    from trendalgo.backtest.fleet_runner import get_fleet_runner

    runner = get_fleet_runner(data_dir)
    snap = runner.start("kraken", "BTC/USD", 1000.0)
    print(
        f"START status={snap['status']} total={snap['total_combinations']} "
        f"lookback_days={snap.get('lookback_days')}"
    )

    active: dict | None = snap
    for i in range(120):
        time.sleep(0.15)
        active = runner.snapshot()
        if not active:
            continue
        if i % 4 == 0:
            print(
                f"  [{active.get('phase')}] {active.get('progress_pct')}% "
                f"{active.get('completed')}/{active.get('total_combinations')} "
                f"elapsed={active.get('elapsed_seconds')}s eta={active.get('eta_seconds')}s "
                f"current={active.get('current_test')}"
            )
        if active.get("status") in ("complete", "error"):
            break

    if not active:
        print("FAIL: no active snapshot")
        return 1
    print(f"DONE status={active.get('status')} phase={active.get('phase')}")
    if active.get("status") == "error":
        print("ERROR:", active.get("error"))
        return 1

    summary = active.get("summary") or {}
    bh = summary.get("buy_and_hold") or {}
    print(f"BUY_HOLD net={bh.get('net_profit')} bars={bh.get('bar_count')}")
    opt = summary.get("final_top10") or summary.get("optimized_top10") or []
    print(f"FINAL_TOP10 count={len(opt)}")
    for row in opt[:10]:
        print(
            f"  #{row.get('rank')} {row.get('strategy_id')} @{row.get('timeframe')} "
            f"net={row.get('net_profit')} tsl={row.get('optimal_tsl_pct', row.get('trailing_stop_pct'))} "
            f"params={row.get('params')}"
        )
    if not opt:
        print("FAIL: final_top10 empty")
        return 1

    history = runner.list_history(limit=5)
    print(f"HISTORY runs={history.get('total', 0)}")
    if not history.get("runs"):
        print("FAIL: history empty")
        return 1
    if not bh:
        print("FAIL: buy_and_hold missing")
        return 1
    print("OK smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
