"""CEX-P2a: document public-market capability vs Opportunity desk."""

from __future__ import annotations

from trendalgo.scanner.public_scan_capability import (
    public_scan_capability,
    tier_ab_public_market_venues,
)


def test_kraken_is_only_opportunity_desk() -> None:
    kraken = public_scan_capability("kraken")
    assert kraken.opportunity_desk
    assert kraken.markets_without_keys
    for eid in ("binanceus", "coinbaseadvanced", "gemini"):
        cap = public_scan_capability(eid)
        assert cap.markets_without_keys
        assert not cap.opportunity_desk


def test_tier_ab_list_includes_kraken() -> None:
    venues = tier_ab_public_market_venues()
    assert "kraken" in venues
    assert "binanceus" in venues
