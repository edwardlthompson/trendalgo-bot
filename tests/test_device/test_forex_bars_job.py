"""FX-AS3/AS5: Forex bars facade prefers Alpaca then AlgoSpecial; interval floor."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from trendalgo.device.forex_bars import fetch_forex_daily_bars
from trendalgo.device.scanner_schedule import FOREX_MIN_INTERVAL, clamp_interval_minutes
from trendalgo.market.types import OhlcvPoint


def _pts() -> list[OhlcvPoint]:
    t0 = int(datetime(2025, 10, 1, tzinfo=UTC).timestamp())
    return [OhlcvPoint(time=t0, open=1.0, high=1.1, low=0.9, close=1.05, volume=10)]


def test_forex_interval_floor_90() -> None:
    assert FOREX_MIN_INTERVAL == 90
    assert clamp_interval_minutes(60, floor=FOREX_MIN_INTERVAL) == 90
    assert clamp_interval_minutes(120, floor=FOREX_MIN_INTERVAL) == 120
    assert clamp_interval_minutes(5) == 60


def test_fetch_forex_daily_uses_alpaca_when_available(tmp_path: Path) -> None:
    until = datetime.now(tz=UTC)
    since = until - timedelta(days=7)
    fake = {"EUR/USD": _pts()}
    with (
        patch("trendalgo.device.forex_bars.alpaca_fx_available", return_value=True),
        patch("trendalgo.device.forex_bars._fetch_alpaca_daily", return_value=fake) as alpaca,
        patch("trendalgo.device.forex_bars.fetch_algospecial_daily") as aspec,
    ):
        out = fetch_forex_daily_bars(tmp_path, ["EUR/USD"], since, until)
    assert out == fake
    alpaca.assert_called_once()
    aspec.assert_not_called()


def test_fetch_forex_daily_falls_back_to_algospecial(tmp_path: Path) -> None:
    until = datetime.now(tz=UTC)
    since = until - timedelta(days=7)
    fake = {"EUR/USD": _pts()}
    progress = MagicMock()
    with (
        patch("trendalgo.device.forex_bars.alpaca_fx_available", return_value=False),
        patch("trendalgo.device.forex_bars.fetch_algospecial_daily", return_value=fake) as aspec,
    ):
        out = fetch_forex_daily_bars(tmp_path, ["EUR/USD"], since, until, progress=progress)
    assert out == fake
    aspec.assert_called_once()
    progress.log.assert_called()
