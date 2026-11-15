"""TF-P2…P4: Alpaca scan → BT → paper (offline)."""

from __future__ import annotations

import pytest

from trendalgo.brokers.alpaca_research import (
    alpaca_buy_hold_bt,
    alpaca_paper_order,
    alpaca_research_bundle,
    alpaca_scan_universe,
)
from trendalgo.device.support_matrix import clear_support_matrix_cache, venue_by_id


def test_alpaca_scan_universe() -> None:
    hits = alpaca_scan_universe()
    assert len(hits) >= 3
    assert all(h.venue == "alpaca" for h in hits)
    assert "AAPL" in {h.symbol for h in hits}


def test_alpaca_buy_hold_bt() -> None:
    result = alpaca_buy_hold_bt("SPY")
    assert result.bar_count >= 1
    assert "synthetic" in result.disclaimer.lower() or "TradFi" in result.disclaimer


def test_alpaca_paper_order() -> None:
    order = alpaca_paper_order("AAPL", "buy", 2.0)
    assert order.mode == "paper_dry_run"
    assert order.status == "simulated"
    with pytest.raises(ValueError):
        alpaca_paper_order("AAPL", "hold", 1.0)


def test_alpaca_research_bundle() -> None:
    bundle = alpaca_research_bundle("MSFT")
    assert bundle["scan_count"] >= 3
    assert bundle["paper"]["status"] == "simulated"
    assert bundle["bt"]["bar_count"] >= 1


def test_matrix_tradfi_research_partial() -> None:
    clear_support_matrix_cache()
    tradfi = venue_by_id("tradfi")
    assert tradfi is not None
    assert tradfi.public_scan in {"thin", "partial"}
    assert tradfi.deep_ohlcv_bt in {"thin", "partial"}
