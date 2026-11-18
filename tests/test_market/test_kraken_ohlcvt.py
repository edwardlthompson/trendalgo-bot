"""Kraken OHLCVT archive reader + tip stitch."""

from __future__ import annotations

import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from trendalgo.market.kraken_ohlcvt import (
    archive_ready,
    clear_ohlcvt_caches,
    load_1m_frame,
    ohlcvt_stems,
    reindex_1m,
    stitch_live_tip,
)


def _write_1m_csv(path: Path, *, days: int = 40, gap_every: int = 7) -> None:
    end = datetime.now(tz=UTC)
    start = end - timedelta(days=days)
    rows: list[str] = []
    ts = int(start.timestamp())
    end_ts = int(end.timestamp())
    px = 100.0
    i = 0
    while ts < end_ts:
        if i % gap_every != 0:
            rows.append(f"{ts},{px},{px + 1},{px - 1},{px + 0.1},1.5,3")
            px += 0.01
        ts += 60
        i += 1
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_ohlcvt_stems_btc() -> None:
    stems = ohlcvt_stems("BTC/USD")
    assert "XBTUSD" in stems
    assert "XXBTZUSD" in stems or "XXBTUSD" in stems


def test_archive_ready_zip_and_dir(tmp_path: Path) -> None:
    assert archive_ready(None) is False
    zpath = tmp_path / "a.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("empty.txt", "x")
    assert archive_ready(zpath) is True
    assert archive_ready(tmp_path) is True


def test_load_1m_from_dir_and_cache(tmp_path: Path) -> None:
    csv = tmp_path / "XBTUSD_1.csv"
    _write_1m_csv(csv)
    cache = tmp_path / "cache"
    frame, stem = load_1m_frame(pair="BTC/USD", archive_path=tmp_path, cache_dir=cache, days=30)
    assert stem == "XBTUSD"
    assert frame is not None
    assert len(frame) >= 30 * 24 * 60 * 0.5  # sparse gaps, but reindexed dense
    # second hit uses cache
    frame2, stem2 = load_1m_frame(pair="BTC/USD", archive_path=tmp_path, cache_dir=cache, days=30)
    assert stem2 == stem
    assert frame2 is not None
    assert len(frame2) == len(frame)


def test_load_1m_from_zip(tmp_path: Path) -> None:
    csv = tmp_path / "XBTUSD_1.csv"
    _write_1m_csv(csv, days=35)
    zpath = tmp_path / "Kraken_OHLCVT_Full.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.write(csv, arcname="XBTUSD_1.csv")
    frame, stem = load_1m_frame(pair="BTC/USD", archive_path=zpath, days=30)
    assert stem == "XBTUSD"
    assert frame is not None
    assert not frame.empty


def test_clear_ohlcvt_caches(tmp_path: Path) -> None:
    assert clear_ohlcvt_caches(None) == 0
    root = tmp_path / "ohlcvt" / "1m"
    root.mkdir(parents=True)
    (root / "XBTUSD.pkl").write_bytes(b"x")
    (root / "ETHUSD.pkl").write_bytes(b"y")
    assert clear_ohlcvt_caches(tmp_path) == 2
    assert list(root.glob("*.pkl")) == []
    assert clear_ohlcvt_caches(tmp_path) == 0


def test_reindex_and_stitch_tip() -> None:
    idx = pd.date_range("2026-11-01", periods=10, freq="2min", tz="UTC")
    base = pd.DataFrame(
        {
            "open": range(10),
            "high": range(1, 11),
            "low": range(10),
            "close": range(10),
            "volume": [1.0] * 10,
        },
        index=idx,
    )
    dense = reindex_1m(base)
    assert len(dense) >= 19
    tip_idx = pd.date_range(
        dense.index[-1] + pd.Timedelta(minutes=1), periods=3, freq="1min", tz="UTC"
    )
    tip = pd.DataFrame(
        {
            "open": [9, 9, 9],
            "high": [10, 10, 10],
            "low": [8, 8, 8],
            "close": [9.5, 9.6, 9.7],
            "volume": [2.0, 2.0, 2.0],
        },
        index=tip_idx,
    )
    merged = stitch_live_tip(dense, tip)
    assert merged.index[-1] == tip_idx[-1]
