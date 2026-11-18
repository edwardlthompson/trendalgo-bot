"""TradFi chart: 7d window trim + overlay uses stamped Alpaca OHLC."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trendalgo.device.scanner_chart_trades import resolve_ohlcv_frame


def _ohlc_hours(n: int = 400) -> list[dict[str, float | int]]:
    base = int(datetime(2025, 10, 1, tzinfo=UTC).timestamp())
    out: list[dict[str, float | int]] = []
    for i in range(n):
        t = base + i * 3600
        px = 100.0 + i * 0.01
        out.append({"t": t, "o": px, "h": px + 1.0, "l": px - 1.0, "c": px + 0.5, "v": 10.0})
    return out


def test_tradfi_display_7d_trims_enrich_ohlc() -> None:
    bars = _ohlc_hours(400)
    coin = {
        "symbol": "AAPL",
        "pair": "AAPL/USD",
        "exchange_id": "tradfi",
        "chart_ohlc_1h": bars,
        "chart_closes_1h": [float(b["c"]) for b in bars],
        "spark_closes_7d": [1.0, 2.0, 3.0],
        "spark_closes_30d": [1.0] * 22,
    }
    full = resolve_ohlcv_frame(coin, timeframe="1h", window="30d")
    week = resolve_ohlcv_frame(coin, timeframe="1h", window="7d")
    assert len(full) > len(week)
    assert len(week) <= 7 * 24 + 2  # calendar trim + DST slack
    span = week.index[-1] - week.index[0]
    assert span <= timedelta(days=8)


def test_tradfi_overlay_uses_lane_ohlc_when_loader_empty(monkeypatch) -> None:
    bars = _ohlc_hours(80)
    coin = {
        "symbol": "AAPL",
        "pair": "AAPL/USD",
        "exchange_id": "tradfi",
        "chart_ohlc_1h": bars,
    }

    def _empty(*_a, **_k):
        return {}, {"data_source": "none"}

    monkeypatch.setattr(
        "trendalgo.device.scan_base_ohlcv.load_scan_frames",
        _empty,
    )
    frame = resolve_ohlcv_frame(coin, timeframe="1h", for_overlay=True)
    assert len(frame) == 80
    assert float(frame["high"].iloc[0]) == float(bars[0]["h"])
