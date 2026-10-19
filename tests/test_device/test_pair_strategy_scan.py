"""Pair All-TA scan: full list, B&H, sort, progress."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from trendalgo.device.pair_scan_progress import progress_line, read_progress, write_progress
from trendalgo.device.pair_strategy_scan import (
    SAUCE_PROGRESS_STEPS,
    collapse_bh_rows,
    ensure_full_catalog,
    scan_pair_strategies,
    sort_rows_by_net,
)
from trendalgo.exchanges.fees import ExchangeFeeSchedule


class _FakeLoaded:
    def __init__(self, frame: pd.DataFrame | None) -> None:
        self.frame = frame


class _FakeLoader:
    def __init__(self, frame: pd.DataFrame | None) -> None:
        self._frame = frame
        self.calls: list[dict[str, Any]] = []

    def load(self, **kwargs: Any) -> _FakeLoaded:
        self.calls.append(dict(kwargs))
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


def test_sauce_progress_steps_constant() -> None:
    assert SAUCE_PROGRESS_STEPS == 2


def test_sort_rows_by_net_descending() -> None:
    rows = [
        {"indicator": "A", "net_pct": 1.0, "win_pct": 50.0, "tsl_hits": 0},
        {"indicator": "B", "net_pct": 9.0, "win_pct": 40.0, "tsl_hits": 0},
        {"indicator": "B&H", "net_pct": 3.0, "win_pct": "-", "tsl_hits": 0},
    ]
    ordered = sort_rows_by_net(rows, descending=True)
    assert [r["indicator"] for r in ordered] == ["B", "B&H", "A"]


def test_sort_rows_tie_break_win_then_tsl_hits() -> None:
    rows = [
        {"indicator": "low_win", "net_pct": 5.0, "win_pct": 40.0, "tsl_hits": 1},
        {"indicator": "high_win", "net_pct": 5.0, "win_pct": 80.0, "tsl_hits": 5},
        {"indicator": "few_hits", "net_pct": 5.0, "win_pct": 80.0, "tsl_hits": 1},
    ]
    ordered = sort_rows_by_net(rows, descending=True)
    assert [r["indicator"] for r in ordered] == ["few_hits", "high_win", "low_win"]


def test_collapse_bh_keeps_best_net() -> None:
    rows = [
        {"indicator": "RSI", "net_pct": 2.0},
        {"indicator": "B&H", "net_pct": 1.0, "timeframe": "1h"},
        {"indicator": "B&H", "net_pct": 4.0, "timeframe": "4h"},
        {"indicator": "EMA", "net_pct": 3.0},
    ]
    out = collapse_bh_rows(rows)
    bh = [r for r in out if r["indicator"] == "B&H"]
    assert len(bh) == 1
    assert bh[0]["net_pct"] == 4.0
    assert len(out) == 3


def test_progress_roundtrip(tmp_path: Path) -> None:
    write_progress(tmp_path, {"message": "Loading ETH 1h…", "done": 1, "total": 10})
    raw = read_progress(tmp_path)
    assert progress_line(raw) == "Loading ETH 1h…"


def test_scan_keeps_losers_and_bh(monkeypatch: Any) -> None:
    fee = ExchangeFeeSchedule(
        exchange_id="kraken",
        taker_pct=0.0026,
        maker_pct=0.0016,
        tier="test",
        source_url="",
        source="test",
    )
    frame = _ohlcv(240)  # enough 1h bars that 4h clears MIN_BARS_FLOOR after resample
    progress: list[str] = []

    tsl_args: list[float] = []

    def fake_backtest_one(
        _frame: Any,
        sid: str,
        *_a: Any,
        **_k: Any,
    ) -> tuple[dict[str, Any] | None, str]:
        tsl_args.append(float(_k.get("trailing_stop_pct") or 0.0))
        # One winner, one loser vs eventual B&H.
        net = 50.0 if sid == "WIN" else -5.0
        return (
            {
                "strategy_id": sid,
                "net_profit": net,
                "trades": 2,
                "win_rate": 0.5,
                "params": {},
                "trailing_stop_pct": 0.0,
                "timeframe": "1h",
            },
            "",
        )

    def fake_bh(*_a: Any, **_k: Any) -> dict[str, Any]:
        return {
            "strategy_id": "B&H",
            "net_profit": 10.0,
            "trades": 1,
            "win_rate": None,
            "params": {},
            "trailing_stop_pct": 0.0,
            "timeframe": "1h",
        }

    monkeypatch.setattr("trendalgo.device.pair_strategy_pass2.backtest_one", fake_backtest_one)
    monkeypatch.setattr("trendalgo.device.pair_strategy_pass2.pass2_worker_count", lambda: 1)
    monkeypatch.setattr("trendalgo.device.pair_strategy_scan.buy_and_hold_row", fake_bh)
    monkeypatch.setattr(
        "trendalgo.device.pair_strategy_scan.oracle_max_row",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr("trendalgo.device.pair_strategy_scan.deepen_seeds", lambda *_a, **_k: [])
    monkeypatch.setattr(
        "trendalgo.device.pair_strategy_scan.coincidence_sauce_row",
        lambda *_a, **_k: None,
    )

    loader = _FakeLoader(frame)
    rows = scan_pair_strategies(
        symbol="ETH",
        pair="ETH/USD",
        timeframes=("1h", "4h"),
        strat_list=("WIN", "LOSE"),
        stake=1000.0,
        fee=fee,
        loader=loader,
        on_progress=lambda p: progress.append(str(p.get("message"))),
    )
    # One network/cache load of 1h — other TFs are resampled in memory.
    assert len(loader.calls) == 1
    assert loader.calls[0].get("timeframe") == "1h"
    assert int(loader.calls[0].get("days") or 0) == 30
    indicators = {str(r.get("indicator")) for r in rows}
    assert "B&H" in indicators
    assert "WIN" in indicators
    assert "LOSE" in indicators
    assert any("resampling" in line.lower() or "Loading" in line for line in progress)
    assert any("complete" in line.lower() for line in progress)
    # Stage A is signal-only (no trailing stop).
    assert tsl_args
    assert all(t == 0.0 for t in tsl_args)


def test_ensure_full_catalog_fills_skips() -> None:
    rows = [
        {"indicator": "RSI", "net_pct": 1.0, "trades": 2},
        {"indicator": "B&H", "net_pct": 2.0, "trades": "-"},
    ]
    filled = ensure_full_catalog(
        rows,
        ("RSI", "ADD", "MACD"),
        symbol="ETH",
        stake_usd=1000.0,
        skips={"ADD": "not_a_strategy", "MACD": "no_trades"},
    )
    inds = {str(r["indicator"]) for r in filled}
    assert inds == {"RSI", "ADD", "MACD", "B&H"}
    assert len(filled) == 4
    add = next(r for r in filled if r["indicator"] == "ADD")
    assert add["skip_reason"] == "not_a_strategy"


def test_scan_full_catalog_length(monkeypatch: Any) -> None:
    fee = ExchangeFeeSchedule(
        exchange_id="kraken",
        taker_pct=0.0026,
        maker_pct=0.0016,
        tier="test",
        source_url="",
        source="test",
    )
    frame = _ohlcv()

    def fake_backtest_one(
        _frame: Any,
        sid: str,
        *_a: Any,
        **_k: Any,
    ) -> tuple[dict[str, Any] | None, str | None]:
        if sid == "ADD":
            return None, "not_a_strategy"
        if sid == "CDLDOJI":
            return None, "no_pattern"
        return (
            {
                "strategy_id": sid,
                "net_profit": 1.0,
                "trades": 1,
                "win_rate": 1.0,
                "params": {},
                "trailing_stop_pct": 0.01,
                "timeframe": "1h",
            },
            None,
        )

    monkeypatch.setattr("trendalgo.device.pair_strategy_pass2.backtest_one", fake_backtest_one)
    monkeypatch.setattr("trendalgo.device.pair_strategy_pass2.pass2_worker_count", lambda: 1)
    monkeypatch.setattr(
        "trendalgo.device.pair_strategy_scan.buy_and_hold_row",
        lambda *_a, **_k: {
            "strategy_id": "B&H",
            "net_profit": 2.0,
            "trades": 1,
            "win_rate": None,
            "params": {},
            "trailing_stop_pct": 0.0,
            "timeframe": "1h",
        },
    )
    monkeypatch.setattr(
        "trendalgo.device.pair_strategy_scan.oracle_max_row",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr("trendalgo.device.pair_strategy_scan.deepen_seeds", lambda *_a, **_k: [])
    monkeypatch.setattr(
        "trendalgo.device.pair_strategy_scan.coincidence_sauce_row",
        lambda *_a, **_k: None,
    )
    strat = ("RSI", "MACD", "ADD", "CDLDOJI")
    rows = scan_pair_strategies(
        symbol="ETH",
        pair="ETH/USD",
        timeframes=("1h",),
        strat_list=strat,
        stake=1000.0,
        fee=fee,
        loader=_FakeLoader(frame),
    )
    assert len(rows) == len(strat) + 1
    skips = {r["indicator"]: r.get("skip_reason") for r in rows if r.get("skip_reason")}
    assert skips["ADD"] == "not_a_strategy"
    assert skips["CDLDOJI"] == "no_pattern"


def test_short_window_keeps_lower_tf_when_24h_skipped(monkeypatch: Any) -> None:
    """Fixed 30d → 24h may lack bars; sheet still uses 1h results for each indicator."""
    fee = ExchangeFeeSchedule(
        exchange_id="kraken",
        taker_pct=0.0026,
        maker_pct=0.0016,
        tier="test",
        source_url="",
        source="test",
    )
    # 80 1h bars → 24h has only a few bars (< MIN_BARS_FLOOR).
    frame = _ohlcv(80)
    progress: list[str] = []

    def fake_backtest_one(
        _frame: Any,
        sid: str,
        *_a: Any,
        timeframe: str = "1h",
        **_k: Any,
    ) -> tuple[dict[str, Any] | None, str | None]:
        return (
            {
                "strategy_id": sid,
                "net_profit": 3.0,
                "trades": 1,
                "win_rate": 1.0,
                "params": {},
                "trailing_stop_pct": 0.01,
                "timeframe": timeframe,
            },
            None,
        )

    monkeypatch.setattr("trendalgo.device.pair_strategy_pass2.backtest_one", fake_backtest_one)
    monkeypatch.setattr("trendalgo.device.pair_strategy_pass2.pass2_worker_count", lambda: 1)
    monkeypatch.setattr(
        "trendalgo.device.pair_strategy_scan.buy_and_hold_row",
        lambda *_a, **_k: {
            "strategy_id": "B&H",
            "net_profit": 1.0,
            "trades": 1,
            "win_rate": None,
            "params": {},
            "trailing_stop_pct": 0.0,
            "timeframe": "1h",
        },
    )
    monkeypatch.setattr(
        "trendalgo.device.pair_strategy_scan.oracle_max_row",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "trendalgo.device.pair_strategy_scan.coincidence_sauce_row",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr("trendalgo.device.pair_strategy_scan.deepen_seeds", lambda *_a, **_k: [])
    rows = scan_pair_strategies(
        symbol="BTC",
        pair="BTC/USD",
        timeframes=("1h", "24h"),
        strat_list=("RSI",),
        stake=1000.0,
        fee=fee,
        loader=_FakeLoader(frame),
        on_progress=lambda p: progress.append(str(p.get("message"))),
    )
    rsi = next(r for r in rows if r["indicator"] == "RSI")
    assert rsi.get("skip_reason") is None
    assert rsi.get("timeframe") == "1h"
    assert any("lower-tf" in line.lower() for line in progress)
