"""TradFi early move/range/top-N cut on mocked daily bars."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from trendalgo.device.lane_scan_filters import LaneScanFilters, save_lane_scan_filters
from trendalgo.device.lts_scan_model import load_lts_rows
from trendalgo.market.types import OhlcvPoint


def _series(n: int, *, start: float, end: float, high_pad: float = 0.01) -> list[OhlcvPoint]:
    base = datetime(2024, 6, 1, tzinfo=UTC)
    out: list[OhlcvPoint] = []
    for i in range(n):
        t = i / max(1, n - 1)
        c = start + (end - start) * t
        out.append(
            OhlcvPoint(
                time=int((base + timedelta(days=i)).timestamp()),
                open=c,
                high=c * (1.0 + high_pad),
                low=c * (1.0 - high_pad),
                close=c,
                volume=1_000_000.0,
            )
        )
    return out


def test_lane_scan_applies_move_range_top_n(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from trendalgo.device.lane_scan_job import lane_scan_job

    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.resolve_alpaca_credentials",
        lambda: ("PK", "SK"),
    )
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.load_tradfi_universe",
        lambda *a, **k: ("FLAT", "MOVA", "MOVB", "MOVC"),
    )
    save_lane_scan_filters(
        tmp_path,
        "tradfi",
        LaneScanFilters(
            min_adv_usd=0,
            min_price=0,
            min_abs_gain_pct=5.0,
            min_range_pct=5.0,
            top_n=2,
        ),
    )
    bars = {
        "FLAT": _series(40, start=100.0, end=100.5, high_pad=0.001),
        "MOVA": _series(40, start=100.0, end=120.0, high_pad=0.05),
        "MOVB": _series(40, start=100.0, end=130.0, high_pad=0.05),
        "MOVC": _series(40, start=100.0, end=115.0, high_pad=0.05),
    }

    def _multi(symbols: list[str], *_a: Any, **_k: Any) -> dict[str, list[OhlcvPoint]]:
        return {s: bars[s] for s in symbols if s in bars}

    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.fetch_alpaca_equity_bars_multi",
        _multi,
    )
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.enrich_lane_coins_1h",
        lambda _r, coins, **_k: coins,
    )
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job._merge_pass1_backtests",
        lambda rows, _root: (list(rows), {"n": len(rows)}),
    )

    result = lane_scan_job(tmp_path, "tradfi")
    assert result["pairs"] == 2
    assert result["filters"]["top_n"] == 2
    rows = load_lts_rows(tmp_path, lane="tradfi")
    assert {r["symbol"] for r in rows} == {"MOVB", "MOVA"}
