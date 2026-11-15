"""Scan OHLCV: OHLCVT deep 1m or exclusive hour/sub-hour bands."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from trendalgo.backtest.heartbeat_tf import exclusive_scan_timeframes
from trendalgo.device.scan_base_ohlcv import load_scan_frames
from trendalgo.device.scan_bt_prefs import ScanBtPrefs, save_scan_bt_prefs, selected_timeframes


def _frame(hours: float, freq: str) -> pd.DataFrame:
    end = datetime(2026, 11, 15, tzinfo=UTC)
    start = end - timedelta(hours=hours)
    idx = pd.date_range(start, end, freq=freq, inclusive="left")
    px = list(range(len(idx)))
    return pd.DataFrame(
        {
            "open": px,
            "high": [v + 1 for v in px],
            "low": [v - 1 for v in px],
            "close": px,
            "volume": [1.0] * len(px),
        },
        index=idx,
    )


def _write_ohlcvt(tmp_path: Path) -> Path:
    end = datetime.now(tz=UTC)
    start = end - timedelta(days=40)
    rows: list[str] = []
    ts = int(start.timestamp())
    end_ts = int(end.timestamp())
    px = 100.0
    while ts < end_ts:
        rows.append(f"{ts},{px},{px + 1},{px - 1},{px + 0.1},1.5,3")
        px += 0.001
        ts += 60
    csv = tmp_path / "XBTUSD_1.csv"
    csv.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return tmp_path


def test_exclusive_scan_timeframes_prefers_hours_when_mixed() -> None:
    assert exclusive_scan_timeframes(["1m", "5m", "1h", "4h"]) == ("1h", "4h")


def test_selected_timeframes_keeps_subhour_only() -> None:
    prefs = ScanBtPrefs(timeframes=["1m", "15m"])
    assert selected_timeframes(prefs) == ("1m", "15m")


def test_load_scan_frames_hour_band_without_ohlcvt(monkeypatch) -> None:
    hour = _frame(30 * 24, "1h")

    class Loader:
        def load(self, **_kw: object) -> SimpleNamespace:
            return SimpleNamespace(frame=hour, source="cache")

    monkeypatch.setattr(
        "trendalgo.device.scan_base_ohlcv_fallback.fetch_tf_frame",
        lambda **_kw: (_ for _ in ()).throw(AssertionError("no live 1m")),
    )
    frames, meta = load_scan_frames(
        symbol="BTC",
        pair="BTC/USD",
        timeframes=("1m", "5m", "1h", "4h"),
        loader=Loader(),
    )
    assert "1m" not in frames and "1h" in frames and "4h" in frames
    assert meta["deep_1m"] is False


def test_load_scan_frames_from_ohlcvt_subhour_only(tmp_path: Path, monkeypatch) -> None:
    archive = _write_ohlcvt(tmp_path)
    save_scan_bt_prefs(tmp_path, ScanBtPrefs(ohlcvt_path=str(archive), ohlcvt_auto_tip=True))

    class Loader:
        def load(self, **_kw: object) -> SimpleNamespace:
            raise AssertionError("loader unused when OHLCVT hits sub-hour")

    tip = _frame(2, "1min")
    monkeypatch.setattr(
        "trendalgo.device.scan_base_ohlcv_fallback.fetch_tf_frame",
        lambda **_kw: tip,
    )
    frames, meta = load_scan_frames(
        symbol="BTC",
        pair="BTC/USD",
        timeframes=("1m", "5m"),
        loader=Loader(),
        prefs_root=tmp_path,
    )
    assert meta["deep_1m"] is True
    assert meta["base_tf"] == "1m"
    assert "1m" in frames and "5m" in frames
    assert "ohlcvt" in str(meta["data_source"])


def test_load_scan_frames_subhour_fallback(monkeypatch) -> None:
    class Loader:
        def load(self, **_kw: object) -> SimpleNamespace:
            raise AssertionError("hour loader must not run")

    monkeypatch.setattr(
        "trendalgo.device.scan_base_ohlcv_fallback.fetch_tf_frame",
        lambda **kw: _frame(12, "1min") if kw.get("timeframe") == "1m" else None,
    )
    frames, meta = load_scan_frames(
        symbol="BTC",
        pair="BTC/USD",
        timeframes=("1m", "5m"),
        loader=Loader(),
    )
    assert "1m" in frames and "5m" in frames
    assert meta["deep_1m"] is False


def test_fetch_tf_frame_builds_dataframe(monkeypatch) -> None:
    from trendalgo.device.scan_base_ohlcv import fetch_1m_frame, fetch_tf_frame

    now = datetime.now(tz=UTC)
    pts = [
        SimpleNamespace(
            time=int((now - timedelta(minutes=i)).timestamp()),
            open=1.0,
            high=2.0,
            low=0.5,
            close=1.5,
            volume=10.0,
        )
        for i in range(60, 0, -1)
    ]
    monkeypatch.setattr(
        "trendalgo.market.ccxt_ohlcv.fetch_exchange_ohlcv",
        lambda *_a, **_k: pts,
    )
    frame = fetch_tf_frame(symbol="BTC", pair="BTCUSD", timeframe="1m", days=1)
    assert frame is not None and len(frame) == 60
    assert fetch_1m_frame(symbol="BTC", pair="BTC/USD", days=1) is not None
