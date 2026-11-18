"""LTS-parity Telegram URL inline keyboard (no callbacks)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from trendalgo.notifications.telegram_coin_fields import (
    coin_symbol,
    exchange_volumes,
    listed_exchanges,
)

__all__ = ["context_keyboard", "primary_market_url", "reply_markup_json"]


def _vol_listed(raw: object) -> bool:
    if raw is None:
        return False
    text = str(raw).strip().upper()
    if not text or text in {"N/A", "NA", "NONE", "NULL"}:
        return False
    try:
        return float(text) > 0
    except ValueError:
        return True


def primary_market_url(coin: dict[str, Any]) -> str:
    explicit = str(coin.get("cmc_url") or "").strip()
    if explicit and "coinmarketcap.com/search" not in explicit.lower():
        return explicit
    slug = str(coin.get("cmc_slug") or coin.get("slug") or "").strip().lower()
    gecko = str(coin.get("gecko_id") or coin.get("cg_id") or "").strip().lower()
    if slug and not (gecko and slug == gecko):
        return f"https://coinmarketcap.com/currencies/{quote(slug, safe='')}/"
    if gecko:
        return f"https://www.coingecko.com/en/coins/{gecko}"
    sym = coin_symbol(coin).lower()
    return f"https://coinmarketcap.com/currencies/{quote(sym, safe='')}/" if sym != "?" else ""


def exchange_url_buttons(coin: dict[str, Any]) -> list[tuple[str, str]]:
    symbol = coin_symbol(coin)
    if symbol == "?":
        return []
    vols = exchange_volumes(coin)
    listed = set(listed_exchanges(coin))
    out: list[tuple[str, str]] = []
    if _vol_listed(vols.get("coinbase")) or "coinbase" in listed:
        out.append(("Coinbase", f"https://www.coinbase.com/advanced-trade/{symbol}-USD"))
    if _vol_listed(vols.get("kraken")) or "kraken" in listed:
        out.append(("Kraken", f"https://pro.kraken.com/app/trade/{symbol.lower()}-usd"))
    if _vol_listed(vols.get("mexc")) or "mexc" in listed:
        out.append(("MEXC", f"https://www.mexc.com/exchange/{symbol}_USDT"))
    return out


def context_keyboard(coin: dict[str, Any]) -> dict[str, Any]:
    """InlineKeyboardMarkup: View Chart | Analyze; then exchange buttons (≤3/row)."""
    symbol = coin_symbol(coin)
    analyze = primary_market_url(coin)
    rows: list[list[dict[str, str]]] = [
        [
            {
                "text": "📈 View Chart",
                "url": f"https://www.tradingview.com/chart/?symbol={symbol}USD",
            },
            {
                "text": "🔍 Analyze Coin",
                "url": analyze or f"https://www.tradingview.com/chart/?symbol={symbol}USD",
            },
        ]
    ]
    exch = [{"text": label, "url": url} for label, url in exchange_url_buttons(coin)]
    for i in range(0, len(exch), 3):
        rows.append(exch[i : i + 3])
    return {"inline_keyboard": rows}


def reply_markup_json(coin: dict[str, Any]) -> str:
    return json.dumps(context_keyboard(coin), separators=(",", ":"))
