"""Sync official exchange + coin icons from CoinGecko into local registry."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from trendalgo.icons.store import IconStore

_REPO = Path(__file__).resolve().parents[3]
_EXCHANGE_CONFIG = _REPO / "config" / "exchange-icons.json"
_WEB_REGISTRY = _REPO / "examples" / "web" / "public" / "icon-registry"
_EXCHANGE_ICON_DIR = _REPO / "examples" / "web" / "public" / "icons" / "exchanges"
_COIN_ICON_DIR = _REPO / "examples" / "web" / "public" / "icons" / "coins"
_COINGECKO = "https://api.coingecko.com/api/v3"
_USER_AGENT = "TrendAlgo-Bot/1.0 (FOSS; icon-registry-sync)"


def _fetch_json(url: str, *, timeout: float = 30.0, retries: int = 4) -> Any:
    last_error: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": _USER_AGENT},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 429 and attempt + 1 < retries:
                time.sleep(3 * (attempt + 1))
                continue
            raise
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(2)
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("fetch failed")


def _extension_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
        if path.endswith(ext):
            return ext
    return ".png"


def _download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=45) as resp:
        dest.write_bytes(resp.read())


def _coingecko_exchange_catalog() -> dict[str, str]:
    catalog: dict[str, str] = {}
    for page in range(1, 5):
        rows = _fetch_json(f"{_COINGECKO}/exchanges?per_page=250&page={page}")
        for row in rows:
            exchange_id = str(row.get("id") or "")
            image = str(row.get("image") or "")
            if exchange_id and image:
                catalog[exchange_id] = image
        if len(rows) < 250:
            break
        time.sleep(2.0)
    return catalog


def _coingecko_exchange_image(exchange_id: str) -> str:
    data = _fetch_json(f"{_COINGECKO}/exchanges/{exchange_id}")
    image = str(data.get("image") or "")
    if not image:
        raise RuntimeError(f"CoinGecko exchange {exchange_id} has no image")
    return image


def sync_exchanges(store: IconStore, *, refresh: bool = False) -> dict[str, Any]:
    raw = json.loads(_EXCHANGE_CONFIG.read_text(encoding="utf-8"))
    exchanges: dict[str, dict[str, Any]] = dict(raw.get("exchanges", {}))
    _EXCHANGE_ICON_DIR.mkdir(parents=True, exist_ok=True)
    catalog: dict[str, str] | None = None

    for exchange_id, meta in exchanges.items():
        remote = str(meta.get("source_url") or "")
        if not remote:
            cg_id = str(meta.get("coingecko_exchange_id") or exchange_id)
            if catalog is None:
                try:
                    catalog = _coingecko_exchange_catalog()
                except urllib.error.HTTPError:
                    catalog = {}
            remote = catalog.get(cg_id, "")
            if not remote:
                remote = _coingecko_exchange_image(cg_id)
            meta["source_url"] = remote
        ext = _extension_from_url(remote)
        dest = _EXCHANGE_ICON_DIR / f"{exchange_id}{ext}"
        if refresh or not dest.exists():
            _download_file(remote, dest)
            time.sleep(0.5)
        local_path = f"/icons/exchanges/{dest.name}"
        meta["icon"] = local_path
        meta["source"] = "coingecko"
        store.upsert_exchange(exchange_id, str(meta["brand"]), str(meta["color"]), local_path)

    _WEB_REGISTRY.mkdir(parents=True, exist_ok=True)
    (_WEB_REGISTRY / "exchanges.json").write_text(
        json.dumps(
            {
                "version": raw.get("version", 2),
                "source": "coingecko",
                "exchanges": exchanges,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"exchange_count": len(exchanges)}


def sync_coins(store: IconStore, *, limit: int = 1000, refresh: bool = False) -> dict[str, Any]:
    coins: dict[str, dict[str, Any]] = {}
    _COIN_ICON_DIR.mkdir(parents=True, exist_ok=True)
    per_page = 250
    pages = (limit + per_page - 1) // per_page

    for page in range(1, pages + 1):
        url = (
            f"{_COINGECKO}/coins/markets"
            f"?vs_currency=usd&order=market_cap_desc&per_page={per_page}&page={page}&sparkline=false"
        )
        try:
            rows = _fetch_json(url)
        except urllib.error.URLError as exc:
            raise RuntimeError(f"CoinGecko page {page} failed: {exc}") from exc
        for row in rows:
            symbol = str(row.get("symbol", "")).upper()
            remote = str(row.get("image") or "")
            if not symbol or not remote:
                continue
            ext = _extension_from_url(remote)
            dest = _COIN_ICON_DIR / f"{symbol}{ext}"
            if refresh or not dest.exists():
                try:
                    _download_file(remote, dest)
                except urllib.error.URLError:
                    continue
                time.sleep(0.15)
            local_path = f"/icons/coins/{dest.name}"
            name = str(row.get("name", symbol))
            coingecko_id = str(row.get("id", symbol.lower()))
            rank = int(row.get("market_cap_rank") or 0)
            entry = {
                "name": name,
                "coingecko_id": coingecko_id,
                "icon": local_path,
                "source_url": remote,
                "rank": rank,
            }
            coins[symbol] = entry
            store.upsert_coin(
                symbol,
                name,
                coingecko_id,
                local_path,
                rank or None,
            )
        if len(rows) < per_page:
            break
        time.sleep(8.0)

    payload = {"version": 2, "source": "coingecko", "count": len(coins), "coins": coins}
    (_WEB_REGISTRY / "coins.json").write_text(json.dumps(payload), encoding="utf-8")
    return {"coin_count": len(coins)}


def migrate_coin_icons_local(store: IconStore, *, refresh: bool = False) -> dict[str, Any]:
    """Download official CoinGecko coin logos from existing registry URLs to local files."""
    path = _WEB_REGISTRY / "coins.json"
    if not path.is_file():
        raise RuntimeError("coins.json missing — run sync with --coins-only first")
    data = json.loads(path.read_text(encoding="utf-8"))
    coins: dict[str, dict[str, Any]] = dict(data.get("coins", {}))
    _COIN_ICON_DIR.mkdir(parents=True, exist_ok=True)
    migrated = 0
    for symbol, meta in coins.items():
        remote = str(meta.get("source_url") or meta.get("icon") or "")
        if not remote.startswith("http"):
            continue
        ext = _extension_from_url(remote)
        dest = _COIN_ICON_DIR / f"{symbol.upper()}{ext}"
        if refresh or not dest.exists():
            try:
                _download_file(remote, dest)
            except urllib.error.URLError:
                continue
            time.sleep(0.12)
        local_path = f"/icons/coins/{dest.name}"
        meta["icon"] = local_path
        meta["source_url"] = remote
        meta["source"] = "coingecko"
        store.upsert_coin(
            symbol.upper(),
            str(meta.get("name", symbol)),
            str(meta.get("coingecko_id", symbol.lower())),
            local_path,
            int(meta.get("rank") or 0) or None,
        )
        migrated += 1
    payload = {
        "version": data.get("version", 2),
        "source": "coingecko",
        "count": len(coins),
        "coins": coins,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return {"coin_count": migrated}


def apply_coin_aliases() -> dict[str, Any]:
    """Duplicate registry entries for exchange ticker aliases (XBT→BTC, etc.)."""
    from trendalgo.icons.aliases import SYMBOL_ALIASES

    path = _WEB_REGISTRY / "coins.json"
    if not path.is_file():
        return {"aliases_added": 0}
    data = json.loads(path.read_text(encoding="utf-8"))
    coins: dict[str, dict[str, Any]] = dict(data.get("coins", {}))
    added = 0
    for alias, canonical in SYMBOL_ALIASES.items():
        base = coins.get(canonical.upper()) or coins.get(canonical)
        if not base:
            continue
        key = alias.upper()
        if key in coins:
            continue
        coins[key] = {**base, "alias_of": canonical.upper()}
        added += 1
    payload = {**data, "coins": coins, "count": len(coins)}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return {"aliases_added": added, "coin_count": len(coins)}


def sync_all(*, coin_limit: int = 1000, refresh: bool = False) -> dict[str, Any]:
    data_dir = Path(os.environ.get("TRENDALGO_DATA_DIR", "data"))
    store = IconStore(data_dir / "icon-registry.db")
    exchanges = sync_exchanges(store, refresh=refresh)
    coins = sync_coins(store, limit=coin_limit, refresh=refresh)
    aliases = apply_coin_aliases()
    return {**exchanges, **coins, **aliases, "db_path": str(store.db_path)}
