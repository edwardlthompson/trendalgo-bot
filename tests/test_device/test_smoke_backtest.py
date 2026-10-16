"""Smoke-backtest CLI helper."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from trendalgo.device.smoke_backtest import run_smoke_backtest


def test_smoke_backtest_rejects_bad_pair() -> None:
    assert run_smoke_backtest("BTCUSD") == 1


def test_smoke_backtest_ok_with_stub(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("TRENDALGO_DEVICE_DIR", str(tmp_path))
    rows = [{"indicator": "RSI", "trades": 4, "skip_reason": None}]
    with patch("trendalgo.device.smoke_backtest.pair_strategy_scan_job", return_value=rows):
        assert run_smoke_backtest("BTC/USD") == 0
