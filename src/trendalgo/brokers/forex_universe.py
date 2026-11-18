"""Load curated Forex pairs for research/BT."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_FALLBACK: tuple[str, ...] = ("EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF", "AUD/USD")


def _default_path() -> Path:
    return Path(__file__).resolve().parents[3] / "config" / "forex_universe.json"


def normalize_fx_pair(pair: str) -> str:
    raw = pair.strip().upper().replace(" ", "").replace("_", "/")
    if "/" not in raw and len(raw) == 6:
        raw = f"{raw[:3]}/{raw[3:]}"
    return raw


@lru_cache(maxsize=4)
def load_forex_universe(path: str | None = None) -> tuple[str, ...]:
    target = Path(path) if path else _default_path()
    if not target.is_file():
        return _FALLBACK
    raw = json.loads(target.read_text(encoding="utf-8"))
    pairs = raw.get("pairs") if isinstance(raw, dict) else raw
    if not isinstance(pairs, list) or not pairs:
        return _FALLBACK
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in pairs:
        pair = normalize_fx_pair(str(item))
        if not pair or pair in seen or "/" not in pair:
            continue
        seen.add(pair)
        cleaned.append(pair)
    return tuple(cleaned) if cleaned else _FALLBACK


def clear_forex_universe_cache() -> None:
    load_forex_universe.cache_clear()


def is_forex_pair(pair: str, *, path: str | None = None) -> bool:
    return normalize_fx_pair(pair) in set(load_forex_universe(path))
