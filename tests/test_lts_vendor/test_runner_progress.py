"""Coin progress events carry skip reasons, and every backtest is reported to the sweep counter."""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any

import pytest

from trendalgo.lts_vendor.backtesting import runner
from trendalgo.lts_vendor.backtesting.backtest_counter import DONE, STEP, CallbackSink


def test_coin_done_event_and_console_line_carry_skip_reasons(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    events: list[dict[str, Any]] = []
    monkeypatch.setattr(runner, "emit_progress", events.append)

    runner._log_progress(
        total=23,
        completed=5,
        failed=0,
        symbol="XYZ",
        status="ok",
        rows=0,
        skipped=2,
        started_at=time.monotonic(),
        skip_reasons={"no_intraday_ohlcv": 2},
    )

    assert events[0]["event"] == "bt_coin_done"
    assert events[0]["skip_reasons"] == {"no_intraday_ohlcv": 2}
    assert "skipped=2 (no_intraday_ohlcv x2)" in capsys.readouterr().out


def test_coin_line_without_reasons_stays_plain(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    events: list[dict[str, Any]] = []
    monkeypatch.setattr(runner, "emit_progress", events.append)

    runner._log_progress(
        total=2,
        completed=1,
        failed=0,
        symbol="BTC",
        status="ok",
        rows=40,
        skipped=0,
        started_at=time.monotonic(),
    )

    assert events[0]["skip_reasons"] == {}
    assert "skipped=0 |" in capsys.readouterr().out


class _FakeLoaded:
    def __init__(self, frame: object | None, skip_reason: str | None = None) -> None:
        self.frame = frame
        self.skip_reason = skip_reason


class _FakeLoader:
    """Loads data for 1h and nothing for 4h, so both the backtest and the skip path run."""

    def load(self, *, symbol: str, timeframe: str, days: int, gecko_id: object) -> _FakeLoaded:
        if symbol == "BAD":
            raise RuntimeError("load_crashed")
        if timeframe == "1h":
            return _FakeLoaded(frame=object())
        return _FakeLoaded(frame=None, skip_reason="no_intraday_ohlcv")


class _NoCache:
    def close(self) -> None:
        return None


def _optimize_fake(*, indicator: str, **_kwargs: object) -> SimpleNamespace:
    if indicator == "MACD":
        raise RuntimeError("boom")
    best = {
        "indicator": indicator,
        "params": {},
        "trailing_stop_pct": None,
        "final_equity": 1100.0,
        "net_pct": 10.0,
        "trades": 4,
        "win_pct": 50.0,
    }
    return SimpleNamespace(
        best_result=best, combos_evaluated=1, stops_tested=0, total_runs=1, skipped_combos=0
    )


def _run_coin(symbol: str, indicators: list[str]) -> dict[str, Any]:
    loader_params: Any = None  # the fake loader ignores it
    return runner._optimize_coin_task(
        symbol=symbol,
        gecko_id=None,
        timeframes=["1h", "4h"],
        indicators=indicators,
        db_path="unused.db",
        cache_age_hours=12,
        max_param_combos=5,
        starting_capital=1000.0,
        fee_bps_round_trip=52.0,
        trailing_stop_min=2,
        trailing_stop_max=4,
        trailing_stop_step=2,
        loader_params=loader_params,
    )


def test_every_backtest_is_reported_then_the_coin_is_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    messages: list[object] = []
    monkeypatch.setattr(runner, "_STEP_SINK", CallbackSink(messages.append))
    monkeypatch.setattr(runner, "PriceCache", lambda _path: _NoCache())
    monkeypatch.setattr(runner, "BacktestDataLoader", lambda **_kwargs: _FakeLoader())
    monkeypatch.setattr(
        runner,
        "compute_buy_and_hold",
        lambda _frame, _config: SimpleNamespace(final_equity=1000.0, net_pct=0.0),
    )
    monkeypatch.setattr(runner, "optimize_indicator", _optimize_fake)

    result = _run_coin("XYZ", ["RSI", "MACD"])

    # 1h: B&H, RSI, MACD (error) = 3. 4h skipped: 1 + 2 indicators = 3. Then the coin closes.
    assert messages == [(STEP, "XYZ")] * 6 + [(DONE, "XYZ")]
    assert [row["indicator"] for row in result["rows"]] == ["B&H", "RSI"]
    reasons = {item["reason"] for item in result["skipped"]}
    assert reasons == {"no_intraday_ohlcv", "optimize_error:boom"}


def test_a_coin_that_crashes_still_closes_its_count(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[object] = []
    monkeypatch.setattr(runner, "_STEP_SINK", CallbackSink(messages.append))
    monkeypatch.setattr(runner, "PriceCache", lambda _path: _NoCache())
    monkeypatch.setattr(runner, "BacktestDataLoader", lambda **_kwargs: _FakeLoader())

    with pytest.raises(RuntimeError, match="load_crashed"):
        _run_coin("BAD", ["RSI"])
    assert messages == [(DONE, "BAD")]


def test_reporting_is_a_quiet_no_op_without_a_sink_or_with_a_failing_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "_STEP_SINK", None)
    runner._report(STEP, "XYZ")  # nobody listening: nothing happens

    class _Broken:
        def put_nowait(self, message: object) -> None:
            raise OSError("pipe closed")

    monkeypatch.setattr(runner, "_STEP_SINK", _Broken())
    runner._report(STEP, "XYZ")  # a dead channel must not fail a backtest


def test_worker_init_installs_the_queue_and_stops_it_blocking_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class _Queue:
        def cancel_join_thread(self) -> None:
            calls.append("cancel_join_thread")

    monkeypatch.setattr(runner, "_STEP_SINK", None)
    queue_stub = _Queue()
    runner._worker_init(queue_stub)
    assert calls == ["cancel_join_thread"]
    assert runner._STEP_SINK is queue_stub
