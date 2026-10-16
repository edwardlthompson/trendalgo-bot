"""Keep prior sparkline closes when a re-fetch returns empty."""

from __future__ import annotations

from typing import Any


def preserve_chart_closes(
    coins: list[dict[str, Any]],
    previous_coins: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Copy closes_1h / closes_1d from previous rows when missing on coins."""
    by_sym = {str(c.get("symbol", "")).upper(): c for c in previous_coins if isinstance(c, dict)}
    for coin in coins:
        sym = str(coin.get("symbol", "")).upper()
        old = by_sym.get(sym) or {}
        for key in ("closes_1h", "closes_1d"):
            cur = coin.get(key)
            if isinstance(cur, list) and len(cur) >= 2:
                continue
            prior = old.get(key)
            if isinstance(prior, list) and len(prior) >= 2:
                coin[key] = prior
    return coins
