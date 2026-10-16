"""LTS-shaped qualified public snapshot store (data dir + sample seed)."""

from __future__ import annotations

import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "qualified_public_snapshot.sample.json"
_FILENAME = "qualified_public_snapshot.json"


def data_dir() -> Path:
    return Path(os.environ.get("TRENDALGO_DATA_DIR", "data")).resolve()


def snapshot_path() -> Path:
    return data_dir() / _FILENAME


def empty_snapshot() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "updated_at": datetime.now(UTC).isoformat(),
        "field_set": "full",
        "scan_interval_seconds": 3600,
        "coins": [],
        "coins_evaluated": 0,
        "errors_count": 0,
    }


def ensure_seeded_snapshot() -> Path:
    """Copy sample fixture into data dir when no live snapshot exists."""
    path = snapshot_path()
    if path.is_file() and path.stat().st_size > 2:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    if _FIXTURE.is_file():
        shutil.copyfile(_FIXTURE, path)
    else:
        path.write_text(json.dumps(empty_snapshot(), indent=2), encoding="utf-8")
    return path


def load_public_snapshot() -> dict[str, Any]:
    path = ensure_seeded_snapshot()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_snapshot()
    if not isinstance(data, dict):
        return empty_snapshot()
    data.setdefault("schema_version", 1)
    data.setdefault("coins", [])
    return data


def write_public_snapshot(payload: dict[str, Any]) -> Path:
    path = snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path


def patch_scan_interval_seconds(interval_seconds: int) -> dict[str, Any]:
    """Update scan_interval_seconds on the live snapshot without re-running a scan."""
    seconds = max(60, int(interval_seconds))
    payload = load_public_snapshot()
    payload["scan_interval_seconds"] = seconds
    write_public_snapshot(payload)
    return payload


def relay_health() -> dict[str, Any]:
    path = snapshot_path()
    exists = path.is_file()
    return {
        "ok": True,
        "has_snapshot": exists,
        "path": str(path),
        "bytes": path.stat().st_size if exists else 0,
        "updated_at": datetime.now(UTC).isoformat(),
    }
