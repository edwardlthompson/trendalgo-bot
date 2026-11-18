"""TradFi/FX 1h enrich stamps HV/DD/Vol Δ and real OHLC wicks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

from trendalgo.device.lane_chart_enrich import enrich_lane_coins_1h, frame_from_lane_ohlc
from trendalgo.device.scanner_chart_trades import frame_from_closes, resolve_ohlcv_frame
from trendalgo.market.types import OhlcvPoint


def _bars(n: int = 240, *, start: float = 100.0) -> list[OhlcvPoint]:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    out: list[OhlcvPoint] = []
    price = start
    for i in range(n):
        o = price
        h = price * 1.02
        low = price * 0.98
        c = price * (1.001 if i % 2 == 0 else 0.999)
        v = 1000.0 + float(i)
        ts = int((base + timedelta(hours=i)).timestamp())
        out.append(OhlcvPoint(time=ts, open=o, high=h, low=low, close=c, volume=v))
        price = c
    return out


def test_enrich_stamps_hv_dd_vol_delta(tmp_path: Path) -> None:
    bars = _bars(240)
    coin: dict[str, Any] = {
        "symbol": "AAPL",
        "pair": "AAPL/USD",
        "exchange_id": "tradfi",
        "chart_closes_1d": [100.0, 101.0, 102.0],
    }

    def fake_fetch(
        root: Path,
        pairs: list[str],
        since: datetime,
        until: datetime,
        *,
        lane: str,
        progress: Any | None = None,
    ) -> dict[str, list[OhlcvPoint]]:
        assert lane == "tradfi"
        assert "AAPL/USD" in pairs
        return {"AAPL/USD": bars}

    with patch("trendalgo.device.lane_chart_enrich.fetch_lane_1h_bars", side_effect=fake_fetch):
        out = enrich_lane_coins_1h(tmp_path, [coin], lane="tradfi")

    assert len(out) == 1
    row = out[0]
    assert row["hv_7d_pct"] is not None
    assert row["max_drawdown_pct"] is not None
    assert row.get("volume_acceleration_pct") is not None
    assert len(row.get("closes_1h") or []) >= 48
    assert len(row.get("chart_ohlc_1h") or []) >= 48
    # Hourly windows for 30d spark (not ~22 daily).
    assert len(row.get("spark_closes_30d") or []) > 22


def test_enrich_soft_fail_empty_bars(tmp_path: Path) -> None:
    coin: dict[str, Any] = {
        "symbol": "ZZZ",
        "pair": "ZZZ/USD",
        "exchange_id": "tradfi",
        "chart_closes_1d": [10.0, 11.0],
    }
    with patch(
        "trendalgo.device.lane_chart_enrich.fetch_lane_1h_bars",
        return_value={},
    ):
        out = enrich_lane_coins_1h(tmp_path, [coin], lane="tradfi")
    row = out[0]
    assert row.get("hv_7d_pct") is None
    assert not row.get("chart_ohlc_1h")


def test_frame_from_lane_ohlc_real_wicks() -> None:
    coin = {
        "chart_ohlc_1h": [
            {"t": 1_700_000_000, "o": 100.0, "h": 105.0, "l": 95.0, "c": 102.0, "v": 10.0},
            {"t": 1_700_003_600, "o": 102.0, "h": 110.0, "l": 100.0, "c": 108.0, "v": 12.0},
        ]
    }
    frame = frame_from_lane_ohlc(coin)
    assert len(frame) == 2
    assert float(frame["high"].iloc[0]) == 105.0
    assert float(frame["low"].iloc[0]) == 95.0
    assert float(frame["high"].iloc[0]) != float(frame["low"].iloc[0])


def test_resolve_ohlcv_frame_tradfi_uses_real_wicks() -> None:
    coin = {
        "symbol": "AAPL",
        "pair": "AAPL/USD",
        "exchange_id": "tradfi",
        "chart_ohlc_1h": [
            {"t": 1_700_000_000, "o": 100.0, "h": 105.0, "l": 95.0, "c": 102.0, "v": 10.0},
            {"t": 1_700_003_600, "o": 102.0, "h": 110.0, "l": 100.0, "c": 108.0, "v": 12.0},
            {"t": 1_700_007_200, "o": 108.0, "h": 112.0, "l": 107.0, "c": 111.0, "v": 11.0},
        ],
        "chart_closes_1h": [102.0, 108.0, 111.0],
    }
    frame = resolve_ohlcv_frame(coin, timeframe="1h")
    assert not frame.empty
    # Real wick path: high != close * 1.001 synthetic.
    assert float(frame["high"].iloc[0]) == 105.0
    assert float(frame["low"].iloc[0]) == 95.0
    synth = frame_from_closes([102.0, 108.0, 111.0])
    assert float(frame["high"].iloc[0]) != float(synth["high"].iloc[0])
