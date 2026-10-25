"""Scanner All-TA uses the same keep rules as Backtest scan_pair_strategies."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pandas as pd

from trendalgo.device.scanner_all_ta_coin import backtest_one_coin


class _FakeLoaded:
    def __init__(self, frame: pd.DataFrame | None) -> None:
        self.frame = frame


class _FakeLoader:
    def __init__(self, frame: pd.DataFrame | None) -> None:
        self._frame = frame

    def load(self, **_kwargs: Any) -> _FakeLoaded:
        return _FakeLoaded(self._frame)


def _ohlcv(n: int = 80) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    close = pd.Series(range(100, 100 + n), index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1.0,
        },
        index=idx,
    )


def test_backtest_one_coin_keeps_losing_pass1_rows() -> None:
    frame = _ohlcv()
    fee = SimpleNamespace(exchange_id="kraken", maker_pct=0.0, taker_pct=0.0026)

    def fake_backtest_one(frame: Any, sid: str, *_a: Any, **_k: Any) -> tuple[dict[str, Any], None]:
        net = -5.0 if sid == "LOSER" else 12.0
        return (
            {
                "strategy_id": sid,
                "net_profit": net,
                "net_pct": net,
                "win_rate": 0.5,
                "trades": 2,
                "params": {},
            },
            None,
        )

    def fake_bh(*_a: Any, **_k: Any) -> dict[str, Any]:
        return {
            "strategy_id": "B&H",
            "net_profit": 10.0,
            "net_pct": 10.0,
            "win_rate": None,
            "trades": 1,
            "params": {},
        }

    with (
        patch("trendalgo.device.pair_strategy_pass2.backtest_one", side_effect=fake_backtest_one),
        patch("trendalgo.device.pair_strategy_scan.buy_and_hold_row", side_effect=fake_bh),
        patch("trendalgo.device.pair_strategy_scan.deepen_seeds", return_value=[]),
    ):
        _sym, rows, _stats, _ctx = backtest_one_coin(
            {"symbol": "TIA", "pair": "TIA/USD"},
            loader_factory=lambda: _FakeLoader(frame),
            timeframes=("1h",),
            strat_list=("WINNER", "LOSER"),
            stake=1000.0,
            fee=fee,
        )
    inds = {str(r.get("indicator") or r.get("strategy_id")) for r in rows}
    assert "LOSER" in inds
    assert "WINNER" in inds
