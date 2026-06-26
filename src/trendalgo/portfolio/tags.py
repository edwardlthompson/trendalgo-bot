"""Asset tags and categories (P14)."""

from __future__ import annotations

from typing import Any

DEFAULT_TAG_MAP: dict[str, str] = {
    "BTC": "L1",
    "ETH": "L1",
    "SOL": "L1",
    "AVAX": "L1",
    "UNI": "DeFi",
    "AAVE": "DeFi",
    "LINK": "DeFi",
    "FET": "AI",
    "RNDR": "AI",
    "TAO": "AI",
    "USD": "Cash",
    "ZUSD": "Cash",
}


def default_tag(asset: str) -> str:
    base = asset.split("-")[0].replace("PERP", "")
    return DEFAULT_TAG_MAP.get(base, DEFAULT_TAG_MAP.get(asset, "Other"))


def tag_holdings(
    holdings: list[dict[str, Any]],
    tag_map: dict[str, str],
) -> list[dict[str, Any]]:
    tagged: list[dict[str, Any]] = []
    for h in holdings:
        asset = str(h["asset"])
        tag = tag_map.get(asset) or default_tag(asset)
        tagged.append({**h, "tag": tag})
    return tagged


def filter_by_tag(holdings: list[dict[str, Any]], tag: str | None) -> list[dict[str, Any]]:
    if not tag:
        return holdings
    return [h for h in holdings if h.get("tag") == tag]
