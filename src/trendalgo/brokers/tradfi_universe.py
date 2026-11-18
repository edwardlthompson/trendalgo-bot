"""TradFi equity universe: live Alpaca assets (cached) → committed top-500 seed."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

_FALLBACK: tuple[str, ...] = ("AAPL", "MSFT", "SPY", "QQQ", "IWM")
_LIVE_FILE = "tradfi_universe_live.json"


def _default_seed_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "tradfi_universe_top500.json"


def _day_bucket(now: datetime | None = None) -> str:
    when = now or datetime.now(tz=UTC)
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return when.astimezone(UTC).strftime("%Y-%m-%d")


@lru_cache(maxsize=8)
def load_seed_universe(path: str | None = None) -> tuple[str, ...]:
    """Committed seed list (exactly ~500 liquid names)."""
    target = Path(path) if path else _default_seed_path()
    if not target.is_file():
        return _FALLBACK
    raw = json.loads(target.read_text(encoding="utf-8"))
    symbols = raw.get("symbols") if isinstance(raw, dict) else raw
    if not isinstance(symbols, list) or not symbols:
        return _FALLBACK
    return _clean_list(symbols) or _FALLBACK


def load_tradfi_universe(
    path: str | None = None,
    *,
    root: Path | None = None,
    refresh: bool = False,
) -> tuple[str, ...]:
    """Prefer live/cached Alpaca assets under ``root``; else seed / fallback.

    Without ``root``, returns the committed seed (tests + offline callers).
    Fresh day-bucket cache is reused; stale/missing triggers a live Assets fetch.
    """
    if root is not None:
        if not refresh and _live_cache_fresh(root):
            live = _load_live_cache(root)
            if live:
                return live
        fetched = _fetch_and_cache_live(root)
        if fetched:
            return fetched
        stale = _load_live_cache(root)
        if stale:
            return stale
    return load_seed_universe(path)


def clear_tradfi_universe_cache() -> None:
    load_seed_universe.cache_clear()


def is_tradfi_symbol(symbol: str, *, path: str | None = None, root: Path | None = None) -> bool:
    sym = symbol.strip().upper().split("/", 1)[0]
    return sym in set(load_tradfi_universe(path, root=root))


def _clean_list(symbols: list[Any]) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in symbols:
        sym = str(item).strip().upper()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        cleaned.append(sym)
    return tuple(cleaned)


def _live_path(root: Path) -> Path:
    return root / _LIVE_FILE


def _load_live_cache(root: Path, *, now: datetime | None = None) -> tuple[str, ...] | None:
    path = _live_path(root)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    bucket = str(raw.get("day") or "")
    symbols = raw.get("symbols")
    if not isinstance(symbols, list) or not symbols:
        return None
    cleaned = _clean_list(symbols)
    if not cleaned:
        return None
    # Stale day → still usable as soft fallback (caller may refresh).
    if bucket == _day_bucket(now):
        return cleaned
    return cleaned  # return anyway; refresh path decides


def _live_cache_fresh(root: Path, *, now: datetime | None = None) -> bool:
    path = _live_path(root)
    if not path.is_file():
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(raw, dict) and str(raw.get("day") or "") == _day_bucket(now)


def _fetch_and_cache_live(root: Path) -> tuple[str, ...] | None:
    try:
        from trendalgo.brokers.alpaca_assets import fetch_tradable_us_equity_symbols

        symbols = fetch_tradable_us_equity_symbols()
    except Exception:  # noqa: BLE001 — soft-fail to seed
        return None
    cleaned = _clean_list(list(symbols))
    if len(cleaned) < 100:
        return None
    _save_live_cache(root, cleaned)
    return cleaned


def _save_live_cache(root: Path, symbols: tuple[str, ...] | list[str]) -> None:
    from trendalgo.device.profile import write_json

    payload = {
        "version": 1,
        "day": _day_bucket(),
        "count": len(symbols),
        "symbols": list(symbols),
    }
    write_json(_live_path(root), payload)
