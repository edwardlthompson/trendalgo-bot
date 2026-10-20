"""External listing URLs for Opportunity scanner name links."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from trendalgo.device.coingecko_ids import resolve_coingecko_id


def coin_listing_url(coin: dict[str, Any]) -> str:
    """Direct coin page: CMC slug, known source_url, else CoinGecko /en/coins/{api_id}.

    Never returns a search page. CoinGecko paths use API ids (bitcoin), not tickers (btc).
    """
    cmc = str(coin.get("cmc_slug") or "").strip()
    if not cmc:
        identity = coin.get("identity") if isinstance(coin.get("identity"), dict) else {}
        cmc = str(identity.get("cmc_slug") or "").strip()
    if cmc:
        return f"https://coinmarketcap.com/currencies/{quote(cmc, safe='-')}/"
    source = str(coin.get("source_url") or "").strip()
    if source.startswith(("http://", "https://")):
        lower = source.lower()
        # Only keep direct coin pages — reject search URLs.
        if "coinmarketcap.com" in lower and "/currencies/" in lower:
            return source
        if "coingecko.com" in lower and "/coins/" in lower and "/search" not in lower:
            return source
    cg = _coingecko_path_id(coin)
    if cg:
        return f"https://www.coingecko.com/en/coins/{quote(cg, safe='-')}"
    if source.startswith(("http://", "https://")) and "/search" not in source.lower():
        return source
    return ""


def _coingecko_path_id(coin: dict[str, Any]) -> str:
    symbol = _base_symbol(coin)
    identity = coin.get("identity") if isinstance(coin.get("identity"), dict) else {}
    hints = (
        coin.get("coingecko_id"),
        coin.get("gecko_id"),
        coin.get("cg_id"),
        identity.get("coingecko_id"),
        identity.get("cg_id"),
        coin.get("slug"),
    )
    hint = next((str(h).strip().lower() for h in hints if str(h or "").strip()), None)
    resolved = resolve_coingecko_id(symbol, hint=hint)
    return resolved or ""


def _base_symbol(coin: dict[str, Any]) -> str:
    raw = str(coin.get("symbol") or "").strip().upper()
    if not raw:
        return ""
    return raw.split("/", 1)[0].strip()
