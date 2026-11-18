"""Persist Forex pairs AlgoSpecial answered with HTTP 404 (skip on later scans)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.brokers.forex_universe import normalize_fx_pair
from trendalgo.device.profile import read_json, write_json

_FILE = "algospecial_fx_unsupported.json"

# Seeded from live scan logs — free OHLC does not list these symbols.
_SEED_UNSUPPORTED: tuple[str, ...] = (
    "EUR/SEK",
    "EUR/NOK",
    "EUR/PLN",
    "EUR/TRY",
    "EUR/HUF",
    "EUR/CZK",
    "EUR/SGD",
    "EUR/MXN",
    "GBP/SEK",
    "GBP/NOK",
    "GBP/SGD",
    "AUD/SGD",
    "NZD/SGD",
    "USD/CNH",
    "USD/INR",
    "USD/THB",
    "USD/KRW",
    "USD/TWD",
    "USD/BRL",
    "USD/CLP",
    "USD/COP",
    "USD/ARS",
)


def unsupported_path(root: Path) -> Path:
    return root / _FILE


def load_unsupported(root: Path) -> set[str]:
    data = read_json(unsupported_path(root))
    pairs: set[str] = {normalize_fx_pair(p) for p in _SEED_UNSUPPORTED}
    if isinstance(data, dict):
        raw = data.get("pairs")
        if isinstance(raw, list):
            for item in raw:
                pair = normalize_fx_pair(str(item))
                if pair and "/" in pair:
                    pairs.add(pair)
    return pairs


def save_unsupported(root: Path, pairs: set[str]) -> None:
    cleaned = sorted({normalize_fx_pair(p) for p in pairs if p and "/" in normalize_fx_pair(p)})
    write_json(unsupported_path(root), {"pairs": cleaned})


def mark_unsupported(root: Path, pair: str) -> set[str]:
    current = load_unsupported(root)
    current.add(normalize_fx_pair(pair))
    save_unsupported(root, current)
    return current


def partition_supported(root: Path, symbols: list[str]) -> tuple[list[str], list[str]]:
    """Split into (live_candidates, already_unsupported)."""
    blocked = load_unsupported(root)
    ok: list[str] = []
    skipped: list[str] = []
    for raw in symbols:
        pair = normalize_fx_pair(raw)
        if pair in blocked:
            skipped.append(pair)
        else:
            ok.append(pair)
    return ok, skipped


def seed_payload() -> dict[str, Any]:
    return {"pairs": list(_SEED_UNSUPPORTED)}
