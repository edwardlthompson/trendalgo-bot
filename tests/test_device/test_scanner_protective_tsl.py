"""Protective TSL stamp: one prepare_signals + mask TSL grid."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.device.scanner_protective_tsl import stamp_lts_protective_tsl
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="kraken",
        taker_pct=0.0026,
        maker_pct=0.0016,
        tier="test",
        source_url="",
        source="test",
    )


def test_stamp_willr_zero_tsl_via_mask_grid(monkeypatch: Any) -> None:
    idx = pd.date_range("2024-01-01", periods=40, freq="h", tz="UTC")
    close = pd.Series(range(100, 140), index=idx, dtype=float)
    frame = pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1.0},
        index=idx,
    )
    row = {
        "indicator": "WILLR",
        "strategy_id": "WILLR",
        "timeframe": "1h",
        "params": {"timeperiod": 14, "entry_level": 30, "exit_level": 70},
        "trailing_stop_pct": 0.0,
        "trailing_stop_loss_pct": 0.0,
        "net_pct": 5.0,
        "trades": 4,
        "wins": 2,
    }
    prepares: list[str] = []

    def fake_prepare(_df: Any, sid: str, params: dict[str, Any] | None = None) -> Any:
        prepares.append(sid)
        n = len(_df)
        entries = np.zeros(n, dtype=bool)
        exits = np.zeros(n, dtype=bool)
        entries[5] = True
        exits[25] = True
        return entries, exits, dict(params or {})

    def fake_assign(
        _frame: Any,
        _entries: Any,
        _exits: Any,
        *,
        fee: Any,
        stake: float,
        signal_net: float | None = None,
        base: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del fee, stake, signal_net
        return {
            **(base or {}),
            "net_profit": 50.0,
            "trades": 4,
            "wins": 3,
            "open_trades": 0,
            "tsl_hits": 0,
            "win_rate": 0.75,
            "trailing_stop_pct": 0.09,
            "protective_tsl": True,
        }

    monkeypatch.setattr("trendalgo.device.scanner_protective_tsl.prepare_signals", fake_prepare)
    monkeypatch.setattr(
        "trendalgo.device.scanner_protective_tsl.assign_protective_tsl_from_masks",
        fake_assign,
    )
    out = stamp_lts_protective_tsl(row, frame, fee=_fee(), stake=100.0)
    assert len(prepares) == 1
    assert float(out["trailing_stop_pct"]) == 9.0
    assert out.get("protective_tsl") is True


def test_stamp_skips_bh() -> None:
    frame = pd.DataFrame({"close": [1.0, 2.0]})
    row = {"indicator": "B&H", "trailing_stop_pct": 0.0, "net_pct": 1.0}
    assert stamp_lts_protective_tsl(row, frame, fee=_fee(), stake=100.0)["trailing_stop_pct"] == 0.0
