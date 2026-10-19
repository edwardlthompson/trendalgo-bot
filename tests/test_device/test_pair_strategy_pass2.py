"""Parallel catalog Pass 2 helper."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from trendalgo.device.pair_strategy_pass2 import pass2_worker_count, run_catalog_pass2
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test", taker_pct=0.0, maker_pct=0.0, tier="retail", source_url=""
    )


def _frame(n: int = 60) -> pd.DataFrame:
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


def test_pass2_worker_count_capped() -> None:
    assert 1 <= pass2_worker_count() <= 8


def test_map_strategies_daemon_uses_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    """WorkerPool daemons cannot spawn ProcessPool children — must use threads."""
    from trendalgo.device import pair_strategy_pass2 as p2

    df = _frame()
    calls: list[str] = []

    def _fake_bt(
        frame: pd.DataFrame,
        sid: str,
        fee: Any,
        stake: float,
        **kwargs: Any,
    ) -> tuple[dict[str, Any] | None, str | None]:
        del frame, fee, stake, kwargs
        calls.append(sid)
        return (
            {
                "strategy_id": sid,
                "indicator": sid,
                "timeframe": "1h",
                "net_profit": 1.0,
                "trades": 1,
                "wins": 1,
                "params": {},
            },
            None,
        )

    class _Daemon:
        daemon = True

    monkeypatch.setattr(p2.multiprocessing, "current_process", lambda: _Daemon())
    monkeypatch.setattr(p2, "backtest_one", _fake_bt)

    def _boom(*_a: Any, **_k: Any) -> list[Any]:
        raise AssertionError("daemonic processes are not allowed to have children")

    monkeypatch.setattr(p2, "_map_process", _boom)
    out = p2._map_strategies(df, "1h", ("A", "B", "C", "D"), _fee(), 1000.0, workers=4)
    assert len(out) == 4
    assert set(calls) == {"A", "B", "C", "D"}


def test_run_catalog_pass2_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _frame()
    calls: list[str] = []

    def _fake_bt(
        frame: pd.DataFrame,
        sid: str,
        fee: Any,
        stake: float,
        **kwargs: Any,
    ) -> tuple[dict[str, Any] | None, str | None]:
        del frame, fee, stake, kwargs
        calls.append(sid)
        return (
            {
                "strategy_id": sid,
                "indicator": sid,
                "timeframe": "1h",
                "net_profit": 10.0,
                "trades": 2,
                "wins": 1,
                "params": {},
            },
            None,
        )

    monkeypatch.setattr("trendalgo.device.pair_strategy_pass2.backtest_one", _fake_bt)
    # Force thread path (workers>1 but process may spawn); still OK with monkeypatch.
    monkeypatch.setattr("trendalgo.device.pair_strategy_pass2.pass2_worker_count", lambda: 2)
    monkeypatch.setattr(
        "trendalgo.device.pair_strategy_pass2._map_process",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("force threads")),
    )
    progress: list[dict[str, Any]] = []
    rows, skips, done = run_catalog_pass2(
        frames_by_tf={"1h": df},
        ordered_tf=("1h",),
        strat_list=("RSI", "MACD", "EMA"),
        fee=_fee(),
        stake=1000.0,
        done_start=0,
        total=3,
        on_progress=progress.append,
    )
    assert done == 3
    assert len(rows) == 3
    assert not skips
    assert set(calls) == {"RSI", "MACD", "EMA"}
    assert any(p.get("phase") == "catalog" for p in progress)
