"""TradFi full-market liquidity/reverse-split filter and daily Market Context fallback."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from trendalgo.device.lane_scan_filters import LaneScanFilters, save_lane_scan_filters
from trendalgo.device.lts_scan_model import load_lts_rows
from trendalgo.market.types import OhlcvPoint


def _steady_series(
    n: int,
    *,
    start: float,
    end: float,
    volume: float,
    high_pad: float = 0.04,
) -> list[OhlcvPoint]:
    base = datetime(2026, 10, 1, tzinfo=UTC)
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
                volume=volume,
            )
        )
    return out


def _reverse_split_series(n: int = 27) -> list[OhlcvPoint]:
    base = datetime(2026, 10, 1, tzinfo=UTC)
    out: list[OhlcvPoint] = []
    for i in range(n):
        c = 0.04 if i < 15 else 2.70  # 67.5x jump on thin volume
        out.append(
            OhlcvPoint(
                time=int((base + timedelta(days=i)).timestamp()),
                open=c,
                high=c * 1.05,
                low=c * 0.95,
                close=c,
                volume=300.0,
            )
        )
    return out


def test_full_market_tradfi_rejects_penny_reverse_splits_and_populates_daily_mc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from trendalgo.device.lane_scan_job import lane_scan_job

    # >500 symbols triggers full_market_tradfi liquidity + reverse-split protection.
    universe = tuple(["SXTC", "ITP", "NVDA", "MSTR", "COIN", *[f"PAD{i}" for i in range(505)]])
    bars: dict[str, list[OhlcvPoint]] = {
        "SXTC": _reverse_split_series(27),
        "ITP": _steady_series(27, start=2.1, end=2.6, volume=30.0),  # ~$72/day ADV
        "NVDA": _steady_series(28, start=118.0, end=152.0, volume=12_000_000.0),
        "MSTR": _steady_series(28, start=54.0, end=78.0, volume=800_000.0),
        "COIN": _steady_series(28, start=76.0, end=103.0, volume=400_000.0),
    }

    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.resolve_alpaca_credentials",
        lambda: ("PK", "SK"),
    )
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.load_tradfi_universe",
        lambda *a, **k: universe,
    )
    save_lane_scan_filters(
        tmp_path,
        "tradfi",
        LaneScanFilters(
            min_adv_usd=0, min_price=0, min_abs_gain_pct=3.0, min_range_pct=5.0, top_n=10
        ),
    )
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.fetch_alpaca_equity_bars_multi",
        lambda symbols, *_a, **_k: {s: bars[s] for s in symbols if s in bars},
    )
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job.enrich_lane_coins_1h",
        lambda _r, coins, **_k: coins,
    )
    # Simulate sparse-1h coins coming back without market_context from pass-1 backtests
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job._merge_pass1_backtests",
        lambda rows, _root: ([{**r, "market_context": None} for r in rows], {"n": len(rows)}),
    )
    monkeypatch.setattr(
        "trendalgo.device.lane_scan_job._prefetch_tradfi_logos",
        lambda _r, _syms: None,
    )

    result = lane_scan_job(tmp_path, "tradfi")
    assert result["pairs"] == 3
    rows = load_lts_rows(tmp_path, lane="tradfi")
    syms = {r["symbol"] for r in rows}
    assert syms == {"NVDA", "MSTR", "COIN"}
    assert "SXTC" not in syms
    assert "ITP" not in syms
    for r in rows:
        mc = r.get("market_context")
        assert isinstance(mc, dict) and mc.get("ok") is True
