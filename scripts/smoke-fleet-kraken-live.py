"""Smoke fleet backtest on live Kraken OHLCV into the program data directory."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=os.environ.get("TRENDALGO_DATA_DIR", "data/dev"))
    parser.add_argument("--exchange", default="kraken")
    parser.add_argument("--pair", default="BTC/USD")
    parser.add_argument("--stake", type=float, default=1000.0)
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TRENDALGO_DATA_DIR"] = str(data_dir.resolve())
    os.environ["TRENDALGO_MARKET_SOURCE"] = "kraken"
    os.environ.setdefault("TRENDALGO_FLEET_FETCH_DELAY_MS", "250")

    from trendalgo.backtest.fleet_runner import get_fleet_runner
    from trendalgo.exchanges.fees import get_fee_store
    store = get_fee_store()
    if store.count() == 0:
        store.seed_from_json()

    from trendalgo.market.fleet_ohlcv import (
        resolve_finest_fetch_timeframe,
        select_tv_timeframes_for_exchange,
    )

    lookback_sec = 30 * 86_400
    finest = resolve_finest_fetch_timeframe(args.exchange, lookback_sec)
    gated = select_tv_timeframes_for_exchange(args.exchange, min_fetch_timeframe=finest)
    print(f"Data dir: {data_dir.resolve()}")
    print(f"Exchange: {args.exchange} · pair: {args.pair} · stake: ${args.stake:.0f}")
    print(f"Finest OHLCV for 30d lookback: {finest}")
    print(f"Fleet timeframes (expected): {', '.join(gated)}")

    runner = get_fleet_runner(data_dir)
    snap = runner.start(args.exchange, args.pair, args.stake)
    print(f"Started job {snap.get('id')} · status={snap.get('status')}")

    active: dict | None = snap
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        time.sleep(2.0)
        active = runner.snapshot()
        if not active:
            continue
        print(
            f"  [{active.get('phase')}] {active.get('progress_pct')}% "
            f"{active.get('completed')}/{active.get('total_combinations')} "
            f"elapsed={active.get('elapsed_seconds')}s eta={active.get('eta_seconds')}s"
        )
        if active.get("status") in ("complete", "error"):
            break

    if not active or active.get("status") != "complete":
        print("FAIL:", active.get("error") if active else "no snapshot")
        return 1

    summary = active.get("summary") or {}
    final_top10 = summary.get("final_top10") or []
    print(f"\nComplete · timeframes tested: {summary.get('timeframes_tested')}")
    print(f"Top 10 count: {len(final_top10)}")
    for row in final_top10[:10]:
        print(
            f"  #{row.get('rank')} {row.get('strategy_id')} @{row.get('timeframe')} "
            f"net=${float(row.get('net_profit', 0)):.2f}"
        )

    db_paths = [
        data_dir / "ohlcv_prices.db",
        data_dir / "prices.db",
        data_dir / "ta_fleet.db",
    ]
    for path in db_paths:
        if path.is_file():
            print(f"DB: {path} ({path.stat().st_size:,} bytes)")

    history = runner.list_history(limit=1)
    print(f"History runs: {history.get('total', 0)} · latest job: {history['runs'][0]['job_id'] if history.get('runs') else 'n/a'}")
    print("Review in app: Backtest tab -> history, or GET /api/v1/backtest/fleet/history")
    return 0 if len(final_top10) >= 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
