"""Persist Scanner host display filters (exchanges + gain text) across launches."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

_FILENAME = "scanner_host_filters.json"
_ALLOWED = frozenset({"coinbase", "kraken"})


def _path() -> Path:
    base = Path(os.environ.get("TRENDALGO_DATA_DIR", "data")).resolve()
    return base / _FILENAME


def default_host_filters() -> dict[str, Any]:
    return {"exchanges": [], "gain7Text": "", "gain30Text": ""}


def normalize_host_filters(raw: dict[str, Any] | None) -> dict[str, Any]:
    src = raw if isinstance(raw, dict) else {}
    exchanges = [
        str(x).strip().lower()
        for x in (src.get("exchanges") or [])
        if str(x).strip().lower() in _ALLOWED
    ]
    return {
        "exchanges": exchanges,
        "gain7Text": str(src.get("gain7Text") or ""),
        "gain30Text": str(src.get("gain30Text") or ""),
    }


def load_host_filters() -> dict[str, Any]:
    path = _path()
    if not path.is_file():
        return default_host_filters()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_host_filters()
    return normalize_host_filters(data if isinstance(data, dict) else None)


def save_host_filters(raw: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_host_filters(raw)
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return normalized
