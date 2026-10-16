"""External listing URLs for Opportunity scanner name links."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote


def coin_listing_url(coin: dict[str, Any]) -> str:
    """Best public page for a coin: CMC slug, CMC/CG source_url, CG slug, else CMC search."""
    cmc = str(coin.get("cmc_slug") or "").strip()
    if cmc:
        return f"https://coinmarketcap.com/currencies/{quote(cmc, safe='')}/"
    source = str(coin.get("source_url") or "").strip()
    if source.startswith(("http://", "https://")):
        lower = source.lower()
        if "coinmarketcap.com" in lower or "coingecko.com" in lower:
            return source
    slug = str(coin.get("slug") or "").strip()
    if slug:
        return f"https://www.coingecko.com/en/coins/{quote(slug, safe='')}"
    if source.startswith(("http://", "https://")):
        return source
    symbol = str(coin.get("symbol") or "").strip()
    if symbol:
        return f"https://coinmarketcap.com/search/?q={quote(symbol)}"
    return ""
