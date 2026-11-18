"""Alpaca band frames for TradFi / Forex All-TA loads."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from trendalgo.device.scan_base_ohlcv import load_scan_frames
from trendalgo.market.types import OhlcvPoint


def _hourly_points(n: int = 800) -> list[OhlcvPoint]:
    end = datetime(2026, 11, 15, tzinfo=UTC)
    start = end - timedelta(hours=n)
    out: list[OhlcvPoint] = []
    ts = int(start.timestamp())
    px = 100.0
    for i in range(n):
        out.append(
            OhlcvPoint(
                time=ts + i * 3600,
                open=px,
                high=px + 1,
                low=px - 1,
                close=px + 0.1,
                volume=1.0,
            )
        )
        px += 0.01
    return out


def test_load_scan_frames_forex_uses_alpaca(tmp_path: Path, monkeypatch: Any) -> None:
    points = _hourly_points()

    def fake_fetch(
        exchange_id: str,
        pair: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> list[OhlcvPoint] | None:
        assert exchange_id == "forex"
        assert timeframe == "1h"
        return points

    monkeypatch.setattr(
        "trendalgo.device.scan_base_ohlcv_alpaca._fetch_points",
        fake_fetch,
    )
    frames, meta = load_scan_frames(
        symbol="EUR",
        pair="EUR/USD",
        timeframes=("1h", "4h"),
        loader=object(),
        prefs_root=tmp_path,
        exchange_id="forex",
    )
    assert "1h" in frames
    assert "4h" in frames
    assert "alpaca:forex" in str(meta.get("data_source") or "")


def test_load_scan_frames_forex_skips_subhour(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "trendalgo.device.scan_base_ohlcv_alpaca._fetch_points",
        lambda *_a, **_k: None,
    )
    frames, meta = load_scan_frames(
        symbol="EUR",
        pair="EUR/USD",
        timeframes=("1m", "5m"),
        loader=object(),
        prefs_root=tmp_path,
        exchange_id="forex",
    )
    assert frames == {}
    assert any("sub-hour" in n.lower() for n in (meta.get("notes") or []))


def test_load_scan_frames_tradfi_hour_band(tmp_path: Path, monkeypatch: Any) -> None:
    points = _hourly_points()

    monkeypatch.setattr(
        "trendalgo.device.scan_base_ohlcv_alpaca._fetch_points",
        lambda *_a, **_k: points,
    )
    frames, meta = load_scan_frames(
        symbol="AAPL",
        pair="AAPL/USD",
        timeframes=("1h", "2h"),
        loader=object(),
        prefs_root=tmp_path,
        exchange_id="tradfi",
    )
    assert "1h" in frames and isinstance(frames["1h"], pd.DataFrame)
    assert not frames["1h"].empty
    assert meta.get("n_frames", 0) >= 1
