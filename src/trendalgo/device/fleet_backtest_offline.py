"""Deterministic fleet backtest for device tests. No network and no TA fleet runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.fleet_backtest_job import fleet_backtest_job

OFFLINE_RESULT: dict[str, Any] = {
    "job_id": "offline01",
    "exchange_id": "kraken",
    "pair": "BTC/USD",
    "stake_usd": 1000.0,
    "top10": [
        {
            "rank": 1,
            "strategy_id": "RSI",
            "timeframe": "60",
            "net_profit": 42.5,
            "trades": 7,
            "trailing_stop_pct": 0.05,
        }
    ],
    "summary": {},
    "buy_and_hold": {"net_profit": 10.0, "strategy_id": "BUY_AND_HOLD"},
}


def offline_fleet_backtest_job(
    profile_root: Path,
    data_dir: Path,
    exchange_id: str,
    pair: str,
    stake_usd: float,
) -> dict[str, Any]:
    return fleet_backtest_job(
        profile_root,
        data_dir,
        exchange_id,
        pair,
        stake_usd,
        _offline_payload=OFFLINE_RESULT,
    )
