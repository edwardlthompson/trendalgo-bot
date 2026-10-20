"""Resolve ticker → CoinGecko API id for direct /en/coins/{id} links.

CoinGecko page paths use the API ``id`` (bitcoin, avalanche-2, hyperliquid), not the
trading symbol. Scanner rows often store slug=symbol.lower(), which 404s for majors.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_API = "https://api.coingecko.com/api/v3"
_UA = "TrendAlgo-Bot/1.0 (FOSS; coingecko-id-resolve)"
_TTL_S = 7 * 24 * 3600
_CACHE_NAME = "coingecko_symbol_ids.json"

# Bootstrap majors (also used offline / tests).
SYMBOL_TO_CG: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "ADA": "cardano",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "AVAX": "avalanche-2",
    "SUI": "sui",
    "NEAR": "near",
    "ATOM": "cosmos",
    "UNI": "uniswap",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "XLM": "stellar",
    "ALGO": "algorand",
    "AAVE": "aave",
    "MKR": "maker",
    "FIL": "filecoin",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "MATIC": "matic-network",
    "POL": "polygon-ecosystem-token",
    "TRX": "tron",
    "SHIB": "shiba-inu",
    "PEPE": "pepe",
    "TON": "the-open-network",
    "ICP": "internet-computer",
    "FLOKI": "floki",
    "HYPE": "hyperliquid",
}


@dataclass
class _IdCache:
    by_symbol: dict[str, str] = field(default_factory=dict)
    ids: set[str] = field(default_factory=set)
    updated_at: float = 0.0


_MEM: _IdCache | None = None


def resolve_coingecko_id(
    symbol: str,
    *,
    hint: str | None = None,
    allow_network: bool = True,
) -> str | None:
    """Return CoinGecko API id for ``symbol``, or None if unknown."""
    sym = _base(symbol)
    if not sym:
        return None
    cache = _cache()
    if sym in cache.by_symbol:
        return cache.by_symbol[sym]
    if sym in SYMBOL_TO_CG:
        cid = SYMBOL_TO_CG[sym]
        _remember(cache, sym, cid)
        return cid
    hint_id = (hint or "").strip().lower()
    if hint_id and _usable_hint(hint_id, sym, cache):
        _remember(cache, sym, hint_id)
        return hint_id
    looked = _icon_registry_id(sym)
    if looked:
        _remember(cache, sym, looked)
        return looked
    if not allow_network or _offline():
        return None
    if _cache_stale(cache):
        _warm_from_markets(cache)
        if sym in cache.by_symbol:
            return cache.by_symbol[sym]
    found = _search_exact_symbol(sym)
    if found:
        _remember(cache, sym, found)
        _save(cache)
        return found
    return None


def _usable_hint(hint: str, symbol: str, cache: _IdCache) -> bool:
    """Accept hint when it is a known CG id, or ticker-equal id already verified."""
    if hint in cache.ids:
        return True
    if hint in SYMBOL_TO_CG.values():
        return True
    if "-" in hint:
        return True
    if hint == symbol.lower():
        return hint in cache.ids or hint in SYMBOL_TO_CG.values()
    return hint != symbol.lower()


def _base(symbol: str) -> str:
    raw = str(symbol or "").strip().upper()
    if not raw:
        return ""
    return raw.split("/", 1)[0].strip()


def _offline() -> bool:
    return os.environ.get("TRENDALGO_OFFLINE", "").strip().lower() in {"1", "true", "yes"}


def _cache() -> _IdCache:
    global _MEM
    if _MEM is not None:
        return _MEM
    path = _cache_path()
    loaded = _IdCache()
    if path is not None and path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            by = {
                str(k).upper(): str(v).lower() for k, v in dict(raw.get("by_symbol") or {}).items()
            }
            loaded = _IdCache(
                by_symbol=by,
                ids=set(by.values()) | {str(x).lower() for x in (raw.get("ids") or [])},
                updated_at=float(raw.get("updated_at") or 0.0),
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            loaded = _IdCache()
    for sym, cid in SYMBOL_TO_CG.items():
        loaded.by_symbol.setdefault(sym, cid)
        loaded.ids.add(cid)
    _MEM = loaded
    return loaded


def _cache_path() -> Path | None:
    try:
        from trendalgo.device.profile import shared_data_dir

        data = shared_data_dir()
        if data is not None:
            return data / _CACHE_NAME
    except Exception:
        pass
    return Path("data") / _CACHE_NAME


def _cache_stale(cache: _IdCache) -> bool:
    if len(cache.by_symbol) < 50:
        return True
    if cache.updated_at <= 0:
        return True
    return (time.time() - cache.updated_at) > _TTL_S


def _remember(cache: _IdCache, symbol: str, cg_id: str) -> None:
    cache.by_symbol[symbol.upper()] = cg_id
    cache.ids.add(cg_id)


def _save(cache: _IdCache) -> None:
    path = _cache_path()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": cache.updated_at or time.time(),
            "by_symbol": dict(sorted(cache.by_symbol.items())),
            "ids": sorted(cache.ids),
        }
        path.write_text(json.dumps(payload, indent=0) + "\n", encoding="utf-8")
    except OSError:
        return


def _icon_registry_id(symbol: str) -> str | None:
    try:
        from trendalgo.device.profile import shared_data_dir
        from trendalgo.icons.store import IconStore

        data = shared_data_dir()
        if data is None:
            return None
        db = data / "icon-registry.db"
        if not db.is_file():
            return None
        row = IconStore(db).get_coin(symbol)
        if not row:
            return None
        cid = str(row.get("coingecko_id") or "").strip().lower()
        return cid or None
    except Exception:
        return None


def _warm_from_markets(cache: _IdCache, *, pages: int = 4) -> None:
    """Fill symbol→id from CoinGecko markets (market-cap order; first wins)."""
    for page in range(1, pages + 1):
        url = (
            f"{_API}/coins/markets?vs_currency=usd&order=market_cap_desc"
            f"&per_page=250&page={page}&sparkline=false"
        )
        try:
            rows = _get_json(url)
        except (OSError, urllib.error.URLError, TimeoutError, ValueError):
            break
        if not isinstance(rows, list) or not rows:
            break
        for row in rows:
            if not isinstance(row, dict):
                continue
            sym = str(row.get("symbol") or "").strip().upper()
            cid = str(row.get("id") or "").strip().lower()
            if not sym or not cid:
                continue
            cache.by_symbol.setdefault(sym, cid)
            cache.ids.add(cid)
        if len(rows) < 250:
            break
        time.sleep(1.2)
    cache.updated_at = time.time()
    _save(cache)


def _search_exact_symbol(symbol: str) -> str | None:
    """Pick best CoinGecko id whose symbol matches exactly (by market_cap_rank)."""
    url = f"{_API}/search?query={urllib.parse.quote(symbol)}"
    try:
        payload = _get_json(url)
    except (OSError, urllib.error.URLError, TimeoutError, ValueError):
        return None
    coins = payload.get("coins") if isinstance(payload, dict) else None
    if not isinstance(coins, list):
        return None
    exact: list[tuple[int, str]] = []
    for row in coins:
        if not isinstance(row, dict):
            continue
        if str(row.get("symbol") or "").upper() != symbol:
            continue
        cid = str(row.get("id") or "").strip().lower()
        if not cid:
            continue
        rank = row.get("market_cap_rank")
        try:
            r = int(rank) if rank is not None else 10_000_000
        except (TypeError, ValueError):
            r = 10_000_000
        exact.append((r, cid))
    if not exact:
        return None
    exact.sort(key=lambda t: t[0])
    return exact[0][1]


def _get_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))
