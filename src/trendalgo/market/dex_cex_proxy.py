"""Labeled CEX spot proxy for DEX research candles (DEX-P2b)."""

from __future__ import annotations

# Default liquid USD/USDC venues for ETH majors.
_PROXY_CEX = "coinbaseadvanced"


def resolve_cex_proxy(venue_id: str, pair: str) -> tuple[str, str]:
    _ = venue_id
    text = pair.strip().upper().replace("-", "/")
    if "/" not in text:
        text = f"{text}/USD"
    # Coinbase Advanced prefers USD; map USDC quote → USD for proxy.
    base, _, quote = text.partition("/")
    if quote in {"USDC", "USDT"}:
        text = f"{base}/USD"
    return _PROXY_CEX, text


def cex_proxy_disclaimer(venue_id: str, cex_id: str) -> str:
    return f"CEX spot proxy via {cex_id} — not DEX swap price; chain venue {venue_id}."
