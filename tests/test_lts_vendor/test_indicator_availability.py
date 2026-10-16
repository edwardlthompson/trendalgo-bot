"""Indicators that need TA-Lib are reported and dropped, and checkpoints are keyed to the sweep."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from trendalgo.lts_vendor.backtesting import runner, signals
from trendalgo.lts_vendor.backtesting.signals import SIGNAL_REGISTRY

TALIB_INDICATORS = ("Stochastic", "CCI", "Ultimate Oscillator", "MFI", "ADX", "Parabolic SAR")


@pytest.fixture
def no_talib(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(signals, "talib", None)


def test_talib_indicators_report_missing_dependency(no_talib: None) -> None:
    for name in TALIB_INDICATORS:
        reason = signals.indicator_unavailable_reason(name)
        assert reason is not None, name
        assert "TA-Lib" in reason, name


def test_pure_pandas_indicators_stay_available(no_talib: None) -> None:
    for name in SIGNAL_REGISTRY:
        if name in TALIB_INDICATORS:
            continue
        assert signals.indicator_unavailable_reason(name) is None, name


def test_unknown_indicator_is_unavailable() -> None:
    assert signals.indicator_unavailable_reason("Not A Real Indicator") == "unknown indicator"


def test_all_indicators_available_when_talib_installed() -> None:
    pytest.importorskip("talib")
    for name in SIGNAL_REGISTRY:
        assert signals.indicator_unavailable_reason(name) is None, name


def test_available_indicators_reports_each_drop(
    no_talib: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[dict[str, Any]] = []
    monkeypatch.setattr(runner, "emit_progress", events.append)

    kept = runner._available_indicators(["RSI", "Stochastic", "MACD"])

    assert kept == ["RSI", "MACD"]
    assert [event["event"] for event in events] == ["bt_indicator_unavailable"]
    assert events[0]["indicator"] == "Stochastic"
    assert "TA-Lib" in events[0]["reason"]


_SWEEP = {"timeframes": ["1h", "4h"], "indicators": ["RSI", "MACD"], "stop_grid": (4, 12, 2)}


def test_checkpoint_path_is_stable_for_one_sweep() -> None:
    base = Path("data/launcher/lts_backtest_checkpoint.json")
    first = runner._sweep_checkpoint_path(base, **_SWEEP)
    assert first.parent == base.parent
    assert first.name.startswith("lts_backtest_checkpoint_")
    assert first.suffix == ".json"
    assert runner._sweep_checkpoint_path(base, **_SWEEP) == first


def test_checkpoint_path_changes_with_indicators_timeframes_and_stops() -> None:
    base = Path("data/launcher/lts_backtest_checkpoint.json")
    first = runner._sweep_checkpoint_path(base, **_SWEEP)
    fewer = {**_SWEEP, "indicators": ["RSI"]}
    other_tf = {**_SWEEP, "timeframes": ["1h"]}
    other_stops = {**_SWEEP, "stop_grid": (4, 10, 2)}
    assert runner._sweep_checkpoint_path(base, **fewer) != first
    assert runner._sweep_checkpoint_path(base, **other_tf) != first
    assert runner._sweep_checkpoint_path(base, **other_stops) != first


def test_checkpoint_path_separates_talib_availability(monkeypatch: pytest.MonkeyPatch) -> None:
    base = Path("data/launcher/lts_backtest_checkpoint.json")
    monkeypatch.setattr(runner, "talib_available", lambda: True)
    with_talib = runner._sweep_checkpoint_path(base, **_SWEEP)
    monkeypatch.setattr(runner, "talib_available", lambda: False)
    without_talib = runner._sweep_checkpoint_path(base, **_SWEEP)
    assert with_talib != without_talib
