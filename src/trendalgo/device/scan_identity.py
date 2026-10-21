"""Qualified-row identity: one row per (exchange_id, symbol)."""

from __future__ import annotations

from typing import Any


def coin_exchange_id(coin: dict[str, Any]) -> str:
    raw = coin.get("exchange_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip().lower()
    listed = coin.get("listed_on")
    if isinstance(listed, list) and listed:
        return str(listed[0]).strip().lower() or "kraken"
    return "kraken"


def coin_symbol(coin: dict[str, Any]) -> str:
    return str(coin.get("symbol") or "").strip().upper()


def row_key(coin: dict[str, Any]) -> str:
    """Stable key for BT merge, NEW badge, and watchlist."""
    return f"{coin_exchange_id(coin)}:{coin_symbol(coin)}"


def watch_key(exchange_id: str, symbol: str) -> str:
    return f"{exchange_id.strip().lower()}:{symbol.strip().upper()}"


def parse_watch_key(raw: str) -> tuple[str, str] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if ":" in text:
        eid, sym = text.split(":", 1)
        eid, sym = eid.strip().lower(), sym.strip().upper()
        if eid and sym:
            return eid, sym
        return None
    # Legacy watchlist: bare symbol or pair → match any exchange.
    sym = text.split("/", 1)[0].strip().upper()
    return ("*", sym) if sym else None


def coin_in_watchlist(coin: dict[str, Any], watch: set[str]) -> bool:
    key = row_key(coin)
    if key in watch:
        return True
    symbol = coin_symbol(coin)
    pair = str(coin.get("pair") or "")
    if symbol and symbol in watch:
        return True
    if pair and pair in watch:
        return True
    for item in watch:
        parsed = parse_watch_key(item)
        if parsed is None:
            continue
        eid, sym = parsed
        if sym == symbol and (eid == "*" or eid == coin_exchange_id(coin)):
            return True
    return False


def stamp_exchange(coin: dict[str, Any], exchange_id: str) -> dict[str, Any]:
    eid = exchange_id.strip().lower() or "kraken"
    out = dict(coin)
    out["exchange_id"] = eid
    out["listed_on"] = [eid]
    return out
