"""Which CEX venues can load public markets without API keys (CEX-P2a)."""

from __future__ import annotations

from dataclasses import dataclass

# Documented CCXT public-market capability for US Tier A/B.
# Kraken remains the only full Opportunity desk; others may load markets but
# are not yet wired into the device public scan pipeline.
_PUBLIC_MARKETS: dict[str, bool] = {
    "kraken": True,
    "binanceus": True,
    "coinbaseadvanced": True,
    "gemini": True,
    "bitstamp": True,
    "cryptocom": False,  # often needs credentials for full markets
    "binance": True,
    "bybit": True,
    "okx": True,
}


@dataclass(frozen=True)
class PublicScanCapability:
    exchange_id: str
    markets_without_keys: bool
    opportunity_desk: bool
    note: str


def public_scan_capability(exchange_id: str) -> PublicScanCapability:
    eid = str(exchange_id or "").strip().lower()
    markets = bool(_PUBLIC_MARKETS.get(eid, False))
    desk = eid == "kraken"
    if desk:
        note = "Full public Opportunity / All-TA / Sauce desk."
    elif markets:
        note = "CCXT public markets possible; Opportunity desk not wired yet."
    else:
        note = "No reliable public markets path without keys."
    return PublicScanCapability(
        exchange_id=eid,
        markets_without_keys=markets,
        opportunity_desk=desk,
        note=note,
    )


def tier_ab_public_market_venues() -> tuple[str, ...]:
    return tuple(
        eid
        for eid, ok in _PUBLIC_MARKETS.items()
        if ok and eid in {"kraken", "binanceus", "coinbaseadvanced", "gemini", "bitstamp"}
    )
