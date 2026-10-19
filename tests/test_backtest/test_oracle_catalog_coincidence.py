"""Oracle×catalog coincidence scorer (fee-aware Sauce TA)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

from trendalgo.backtest.oracle_catalog_coincidence import (
    coincidence_sauce_row,
    hit_rate,
    score_catalog_vs_oracle,
)
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee(*, taker: float = 0.0) -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test", taker_pct=taker, maker_pct=0.0, tier="retail", source_url=""
    )


def _frame(n: int = 80) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    close = 100.0 + np.cumsum(np.random.default_rng(2).normal(0, 0.4, size=n))
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(n, 10.0),
        },
        index=idx,
    )


def test_hit_rate_window() -> None:
    fires = np.zeros(20, dtype=bool)
    fires[5] = True
    assert hit_rate(fires, [5]) == 1.0
    assert hit_rate(fires, [6]) == 1.0
    assert hit_rate(fires, [8]) == 0.0


def test_score_and_coincidence(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _frame()
    entries = np.zeros(len(df), dtype=bool)
    exits = np.zeros(len(df), dtype=bool)
    entries[10] = True
    entries[30] = True
    exits[20] = True
    exits[40] = True

    def _fake_prep(_df: pd.DataFrame, sid: str, _params: object) -> tuple:
        if sid in {"RSI", "MACD"}:
            return entries, exits, {}
        return None, None, "skip"

    monkeypatch.setattr(
        "trendalgo.backtest.oracle_catalog_coincidence.prepare_signals",
        _fake_prep,
    )
    catalog = [
        {
            "indicator": "RSI",
            "strategy_id": "RSI",
            "timeframe": "1h",
            "net_pct": 12.0,
            "params": {},
        },
        {
            "indicator": "MACD",
            "strategy_id": "MACD",
            "timeframe": "1h",
            "net_pct": 8.0,
            "params": {},
        },
    ]
    e_row, x_row = score_catalog_vs_oracle(
        df, catalog, entry_labels=[10, 30], exit_labels=[20, 40], timeframe="1h"
    )
    assert e_row is not None and e_row["indicator"] == "RSI"
    assert x_row is not None
    oracle = {
        "timeframe": "1h",
        "oracle_swings": [
            {"entry_index": 10, "exit_index": 20},
            {"entry_index": 30, "exit_index": 40},
        ],
    }
    sauce = coincidence_sauce_row(df, oracle, catalog, fee=_fee(), stake=1000.0, symbol="BTC")
    assert sauce is not None
    assert sauce.get("indicator") == "Secret Sauce TA"
    assert sauce.get("ss_coincidence") is True
    assert (sauce.get("params") or {}).get("ss_ta_fee_aware") is True


def test_fee_aware_picks_net_over_hit_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    """High Oracle hit-rate pair can lose; fee-aware picks the profitable combo."""
    n = 60
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    # Rising then falling: only a few well-timed trades profit.
    close = np.concatenate([np.linspace(100.0, 120.0, 30), np.linspace(120.0, 100.0, 30)])
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(n, 10.0),
        },
        index=idx,
    )
    # HIHIT: fires on every oracle label (±1) but also spammy elsewhere → fee bleed.
    hi_e = np.zeros(n, dtype=bool)
    hi_x = np.zeros(n, dtype=bool)
    for i in range(0, n, 3):
        hi_e[i] = True
        hi_x[min(n - 1, i + 1)] = True
    # LOWHIT: only two good trough→peak style trades.
    lo_e = np.zeros(n, dtype=bool)
    lo_x = np.zeros(n, dtype=bool)
    lo_e[5] = True
    lo_x[25] = True
    lo_e[35] = True
    lo_x[55] = True

    masks = {
        "HIHIT": (hi_e, hi_x),
        "LOWHIT": (lo_e, lo_x),
    }

    def _fake_prep(_df: pd.DataFrame, sid: str, _params: object) -> tuple:
        if sid not in masks:
            return None, None, "skip"
        e, x = masks[sid]
        return e, x, {}

    def _fake_sim(
        _df: pd.DataFrame,
        entries: Any,
        exits: Any,
        *,
        stake_usd: float,
        fee: Any,
        trailing_stop_pct: float = 0.0,
        collect_trades: bool = False,
    ) -> dict[str, Any]:
        del _df, fee, trailing_stop_pct, stake_usd
        e = np.asarray(entries, dtype=bool)
        x = np.asarray(exits, dtype=bool)
        e_spam = int(e.sum()) >= 10
        x_spam = int(x.sum()) >= 10
        if e_spam or x_spam:
            net, trades = -50.0, 15
            trade_list = [{"entry_index": 0, "exit_index": 2}] * 3
        else:
            net, trades = 80.0, 4
            trade_list = [
                {"entry_index": 5, "exit_index": 25},
                {"entry_index": 35, "exit_index": 55},
                {"entry_index": 5, "exit_index": 25},
                {"entry_index": 35, "exit_index": 55},
            ]
        out: dict[str, Any] = {
            "net_profit": net,
            "gross_profit": net,
            "fees_paid": 5.0,
            "trades": trades,
            "wins": max(0, trades - 1),
        }
        if collect_trades:
            out["trade_list"] = trade_list
        return out

    monkeypatch.setattr(
        "trendalgo.backtest.oracle_catalog_coincidence.prepare_signals",
        _fake_prep,
    )
    monkeypatch.setattr(
        "trendalgo.backtest.oracle_catalog_coincidence.simulate_long_with_fees",
        _fake_sim,
    )
    catalog = [
        {
            "indicator": "HIHIT",
            "strategy_id": "HIHIT",
            "timeframe": "1h",
            "net_pct": 99.0,
            "params": {},
        },
        {
            "indicator": "LOWHIT",
            "strategy_id": "LOWHIT",
            "timeframe": "1h",
            "net_pct": 1.0,
            "params": {},
        },
    ]
    oracle = {
        "timeframe": "1h",
        "oracle_swings": [
            {"entry_index": 5, "exit_index": 25},
            {"entry_index": 35, "exit_index": 55},
            {"entry_index": 8, "exit_index": 28},
        ],
    }
    # Hit-rate alone would prefer HIHIT (fires near every label).
    e_row, x_row = score_catalog_vs_oracle(
        df, catalog, entry_labels=[5, 35, 8], exit_labels=[25, 55, 28], timeframe="1h"
    )
    assert e_row is not None and e_row["strategy_id"] == "HIHIT"
    assert x_row is not None and x_row["strategy_id"] == "HIHIT"

    sauce = coincidence_sauce_row(
        df, oracle, catalog, fee=_fee(taker=0.0026), stake=1000.0, symbol="BTC"
    )
    assert sauce is not None
    params = sauce.get("params") or {}
    assert params.get("coincidence_entry") == "LOWHIT"
    assert params.get("coincidence_exit") == "LOWHIT"
    assert float(sauce.get("net_pct") or 0.0) > 0.0
