"""Real closes_1h / closes_1d attachment for Scanner charts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from trendalgo.lts_vendor.bridge import opportunities_to_final_results
from trendalgo.lts_vendor.chart_closes import (
    attach_chart_closes,
    gain_pct_from_closes,
)
from trendalgo.lts_vendor.chart_preserve import preserve_chart_closes
from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot


def _bars(n: int, *, start: float = 100.0, step: float = 0.5) -> list[OhlcvPoint]:
    base = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
    return [
        OhlcvPoint(
            time=base + i * 3600,
            open=start + i * step,
            high=start + i * step + 1,
            low=start + i * step - 1,
            close=start + i * step,
            volume=1.0,
        )
        for i in range(n)
    ]


def test_gain_pct_from_closes() -> None:
    assert gain_pct_from_closes([100.0, 110.0]) == pytest.approx(10.0)
    assert gain_pct_from_closes([100.0]) is None
    assert gain_pct_from_closes([0.0, 10.0]) is None


def test_fetch_chart_closes_soft_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_CHART_WORKERS", "bad")
    from trendalgo.lts_vendor.chart_closes import fetch_chart_closes_for_pair

    def boom(*_a, **_k):
        raise RuntimeError("kraken down")

    h, d = fetch_chart_closes_for_pair("SOL/USD", fetch_ohlcv=boom)
    assert h == [] and d == []


def test_attach_empty_closes_clears_keys() -> None:
    coins = [{"symbol": "SOL", "closes_1h": [1.0], "closes_1d": [2.0], "gains": {}, "identity": {}}]
    out = attach_chart_closes(coins, lambda _s: "SOL/USD", fetch_ohlcv=lambda *_a, **_k: [])
    assert "closes_1h" not in out[0]
    assert "closes_1d" not in out[0]


def test_preserve_chart_closes_fills_gaps() -> None:
    coins = [{"symbol": "SOL", "gains": {}}]
    prev = [{"symbol": "SOL", "closes_1h": [1.0, 2.0], "closes_1d": [3.0, 4.0]}]
    out = preserve_chart_closes(coins, prev)
    assert out[0]["closes_1h"] == [1.0, 2.0]
    assert out[0]["closes_1d"] == [3.0, 4.0]


def test_attach_chart_closes_parallel_pairs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_CHART_WORKERS", "4")
    h_bars = _bars(50)
    d_bars = _bars(10)

    def fake_fetch(pair: str, timeframe: str, since: object, until: object, **kwargs: object):
        return h_bars if timeframe == "1h" else d_bars

    coins = [
        {"symbol": "SOL", "gains": {}, "identity": {}},
        {"symbol": "DOT", "gains": {}, "identity": {}},
        {"symbol": "", "gains": {}, "identity": {}},
    ]
    out = attach_chart_closes(
        coins,
        lambda s: f"{s}/USD",
        fetch_ohlcv=fake_fetch,
    )
    assert len(out[0]["closes_1h"]) == 50
    assert len(out[1]["closes_1d"]) == 10
    assert "closes_1h" not in out[2]


def test_attach_chart_closes_no_synthetic() -> None:
    h_bars = _bars(200, start=50.0, step=0.1)
    d_bars = _bars(30, start=50.0, step=1.0)

    def fake_fetch(pair: str, timeframe: str, since: object, until: object, **kwargs: object):
        assert pair == "SOL/USD"
        if timeframe == "1h":
            return h_bars
        if timeframe == "1d":
            return d_bars
        return []

    coins = [
        {
            "symbol": "SOL",
            "gains": {"7d": 0.0, "30d": 0.0},
            "identity": {},
        }
    ]
    out = attach_chart_closes(coins, lambda _s: "SOL/USD", fetch_ohlcv=fake_fetch)
    assert len(out[0]["closes_1h"]) == 200
    assert len(out[0]["closes_1d"]) == 30
    assert out[0]["closes_1h"][0] == 50.0


def test_attach_chart_closes_30d_from_trimmed_1h_not_full_series() -> None:
    from trendalgo.backtest.load_days import SCAN_LOOKBACK_HOURS
    from trendalgo.lts_vendor.chart_closes import _apply_closes

    # Crash early then late rally — full-series gain differs from last-30d 1h gain.
    early = [100.0 - i * 0.1 for i in range(500)]
    late_start = early[-1]
    late = [late_start + i * 0.05 for i in range(SCAN_LOOKBACK_HOURS)]
    h1 = early + late
    coin: dict = {"gains": {}, "identity": {}}
    _apply_closes(coin, h1, [20.0, 25.0])  # daily would imply +25% if used for 30d
    assert len(coin["closes_1h"]) == SCAN_LOOKBACK_HOURS
    expect = gain_pct_from_closes(h1[-SCAN_LOOKBACK_HOURS:])
    assert coin["gains"]["30d"] == pytest.approx(expect)
    full = gain_pct_from_closes(h1)
    assert abs(float(coin["gains"]["30d"]) - float(full or 0.0)) > 1.0


def test_opportunities_to_final_results_uses_pair_and_fetcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    h_bars = _bars(180)
    d_bars = _bars(20)

    def fake_fetch(pair: str, timeframe: str, since: object, until: object, **kwargs: object):
        assert pair == "LINK/USD"
        return h_bars if timeframe == "1h" else d_bars

    monkeypatch.setattr("trendalgo.market.kraken.fetch_ohlcv", fake_fetch)

    snap = QualifiedSnapshot(
        generated_at=datetime.now(UTC),
        as_of=datetime.now(UTC),
        scan_id=1,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="LINK/USD",
                uniformity=0.6,
                gain_pct=0.01,
                volume_score=1.0,
                entry_signal=True,
                sparkline=[1.0, 2.0],
            )
        ],
    )
    coins = opportunities_to_final_results(snap)
    assert len(coins) == 1
    assert len(coins[0]["closes_1h"]) == 180
    assert len(coins[0]["closes_1d"]) == 20
    assert coins[0]["closes_1h"] != [100.0 + i * 0.1 for i in range(168)]
