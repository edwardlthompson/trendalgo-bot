"""Per-pair Results dialog column-filter memory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json

_FILE = "results_pair_filters.json"


def _key(pair: str) -> str:
    return (pair or "").strip().upper() or "UNKNOWN"


def load_pair_filters(root: Path, pair: str) -> dict[str, Any]:
    raw = read_json(root / _FILE)
    if not isinstance(raw, dict):
        return {}
    block = raw.get(_key(pair))
    return dict(block) if isinstance(block, dict) else {}


def save_pair_filters(root: Path, pair: str, filters: dict[str, Any]) -> None:
    path = root / _FILE
    prior = read_json(path)
    payload: dict[str, Any] = dict(prior) if isinstance(prior, dict) else {}
    payload[_key(pair)] = dict(filters)
    write_json(path, payload)
