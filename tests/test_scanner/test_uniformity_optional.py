"""Board pipeline ignores uniformity (schema field stays 0)."""

from __future__ import annotations

import pytest

from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner.config import ScannerSettings
from trendalgo.scanner.live_market import LiveMarketRow
from trendalgo.scanner.pipeline import run_pipeline

_PAIR = "BTC/USD"


def _noisy_bars() -> list[OhlcvPoint]:
    """Bars that would score poorly on uniformity if scored."""
    closes = [
        100,
        110,
        90,
        120,
        80,
        130,
        70,
        140,
        60,
        150,
        55,
        145,
        65,
        135,
        75,
        125,
        85,
        115,
        95,
        105,
        100,
        108,
        92,
        112,
        88,
    ]
    bars: list[OhlcvPoint] = []
    ts = 1_700_000_000
    for i, close in enumerate(closes):
        bars.append(
            OhlcvPoint(
                time=ts + i * 300,
                open=close,
                high=close * 1.02,
                low=close * 0.98,
                close=close,
                volume=1000,
            )
        )
    return bars


@pytest.fixture
def listed_btc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)
    monkeypatch.setattr(
        "trendalgo.scanner.pipeline.verify_kraken_listings",
        lambda: (_PAIR,),
    )


def test_pipeline_qualifies_without_uniformity(listed_btc: None) -> None:
    row = LiveMarketRow(
        pair=_PAIR,
        bars=_noisy_bars(),
        gain_pct=0.05,
        volume_usd=2_000_000,
    )
    funnel: dict = {}
    settings = ScannerSettings(
        min_volume_usd=100_000,
        min_gain_pct=0.0,
        min_uniformity=0.35,  # coerced to 0; board never gates on it
    )
    snap = run_pipeline(
        settings,
        fetcher=lambda _pairs: [row],
        funnel_out=funnel,
    )
    pairs = {o.pair for o in snap.opportunities}
    assert _PAIR in pairs
    assert snap.opportunities[0].uniformity == 0.0
    assert funnel.get("qualified_n") == 1
    assert "min_uniformity" not in funnel
