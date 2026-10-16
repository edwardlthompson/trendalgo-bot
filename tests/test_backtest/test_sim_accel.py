"""Accel backend parity and TSL grid fees."""

from __future__ import annotations

import numpy as np

from trendalgo.backtest.sim_accel import (
    accel_backend,
    python_one,
    simulate_arrays,
    simulate_tsl_grid,
)
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _series() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    closes = np.array([100.0, 100.0, 110.0, 105.0, 120.0, 100.0], dtype=np.float64)
    entries = np.array([False, True, False, False, False, False])
    exits = np.array([False, False, False, True, False, False])
    return closes, entries, exits


def test_accel_backend_known() -> None:
    assert accel_backend() in {"cuda", "numba", "python"}


def test_simulate_arrays_matches_python() -> None:
    closes, entries, exits = _series()
    fee_per = 5.2
    py = python_one(closes, entries, exits, 1000.0, fee_per, 0.05)
    got = simulate_arrays(
        closes, entries, exits, stake_usd=1000.0, fee_per_trade=fee_per, trailing_stop_pct=0.05
    )
    assert got == py
    assert len(py) == 6


def test_open_trade_at_last_bar_not_counted_as_win() -> None:
    closes = np.array([100.0, 100.0, 110.0, 120.0], dtype=np.float64)
    entries = np.array([False, True, False, False])
    exits = np.array([False, False, False, False])
    gross, fees, trades, wins, hits, open_n = python_one(closes, entries, exits, 1000.0, 5.2, 0.0)
    assert trades == 1
    assert open_n == 1
    assert wins == 0
    assert hits == 0
    assert gross > 0


def test_tsl_grid_fees_subtract_from_net() -> None:
    closes, entries, exits = _series()
    fee = ExchangeFeeSchedule(
        exchange_id="kraken",
        taker_pct=0.0026,
        maker_pct=0.0016,
        tier="test",
        source_url="",
        source="test",
    )
    rows = simulate_tsl_grid(closes, entries, exits, (0.01, 0.02, 0.05), stake_usd=1000.0, fee=fee)
    assert len(rows) == 3
    for row in rows:
        assert abs(row["net_profit"] - (row["gross_profit"] - row["fees_paid"])) < 1e-6
        if row["trades"] > 0:
            assert row["fees_paid"] > 0
