"""Protective TSL stamp uses backtest_one grid (not empty re-prepare masks)."""

from __future__ import annotations

from typing import Any

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


def test_stamp_willr_zero_tsl_via_backtest_one(monkeypatch: Any) -> None:
    idx = pd.date_range("2024-01-01", periods=40, freq="h", tz="UTC")
    close = pd.Series(range(100, 140), index=idx, dtype=float)
    frame = pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1.0},
        index=idx,
    )
    row = {
        "indicator": "WILLR",
        "timeframe": "1h",
        "params": {"timeperiod": 14, "entry_level": 30, "exit_level": 70},
        "trailing_stop_pct": 0.0,
        "trailing_stop_loss_pct": 0.0,
        "net_pct": 5.0,
        "trades": 4,
        "wins": 2,
    }

    def fake_bt(
        _df: Any,
        sid: str,
        _fee: Any,
        _stake: float,
        **kw: Any,
    ) -> tuple[dict[str, Any] | None, str | None]:
        tsl = float(kw.get("trailing_stop_pct") or 0.0)
        # Plateau: 8–20% equal & unhit → pick 9%.
        net = 50.0 if tsl >= 0.08 else 40.0 - tsl * 100.0
        hits = 0 if tsl >= 0.08 else 2
        return (
            {
                "strategy_id": sid,
                "net_profit": net,
                "trades": 4,
                "wins": 3,
                "open_trades": 0,
                "tsl_hits": hits,
                "win_rate": 0.75,
                "trailing_stop_pct": tsl,
            },
            None,
        )

    monkeypatch.setattr("trendalgo.device.scanner_protective_tsl.backtest_one", fake_bt)
    out = stamp_lts_protective_tsl(row, frame, fee=_fee(), stake=100.0)
    assert float(out["trailing_stop_pct"]) == 9.0
    assert out.get("protective_tsl") is True


def test_stamp_skips_bh() -> None:
    frame = pd.DataFrame({"close": [1.0, 2.0]})
    row = {"indicator": "B&H", "trailing_stop_pct": 0.0, "net_pct": 1.0}
    assert stamp_lts_protective_tsl(row, frame, fee=_fee(), stake=100.0)["trailing_stop_pct"] == 0.0
