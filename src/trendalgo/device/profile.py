"""Device profile folder: the databases and small JSON files this PC keeps (ADR-0016).

Every JSON write is atomic (temp file, fsync, rename), so an interrupted save never leaves a half file.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

_PATH_LOCKS: dict[str, threading.Lock] = {}
_PATH_LOCKS_GUARD = threading.Lock()
_REPLACE_TRIES = 8


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve()) if path.parent.exists() else str(path)
    with _PATH_LOCKS_GUARD:
        lock = _PATH_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _PATH_LOCKS[key] = lock
        return lock


PROFILE_ENV = "TRENDALGO_DEVICE_DIR"
CANDLES_ENV = "TRENDALGO_CANDLES_DB"
DATA_ENV = "TRENDALGO_DATA_DIR"
PORTFOLIO_ENV = "TRENDALGO_PORTFOLIO_DB"
DEFAULT_PROFILE = Path.home() / ".trendalgo" / "device"
SCANNER_DB = "scanner.db"
BOTS_DB = "bots.db"
JOURNAL_DB = "journal.db"
CANDLES_DB = "ohlcv_prices.db"
PORTFOLIO_DB = "portfolio.db"
SETTINGS_FILE = "settings.json"
PLAN_FILE = "plan.json"
LOCK_FILE = "device.lock"
EXPORTS_DIR = "exports"
DEVICE_LOG = "device.log"


class ProfileError(RuntimeError):
    """A profile file exists but cannot be read. It is never replaced silently."""


def profile_dir() -> Path:
    raw = os.environ.get(PROFILE_ENV, "").strip()
    return Path(raw) if raw else DEFAULT_PROFILE


def shared_data_dir() -> Path | None:
    """The API's data folder when TRENDALGO_DATA_DIR is set. The device reads it and never owns it."""
    raw = os.environ.get(DATA_ENV, "").strip()
    return Path(raw) if raw else None


def db_paths(root: Path) -> dict[str, Path]:
    """Database paths. TRENDALGO_DATA_DIR points scanner, bots, journal, and candles at the API's
    data folder. CANDLES_ENV overrides the candle file alone."""
    data = shared_data_dir() or root
    override = os.environ.get(CANDLES_ENV, "").strip()
    return {
        "scanner": data / SCANNER_DB,
        "bots": data / BOTS_DB,
        "journal": data / JOURNAL_DB,
        "candles": Path(override) if override else data / CANDLES_DB,
    }


def read_json(path: Path) -> dict[str, Any] | None:
    """The object stored in path, or None when the file is missing. A corrupt file raises."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProfileError(f"{path.name} cannot be read. Move it aside, then try again.") from exc
    if not isinstance(data, dict):
        raise ProfileError(f"{path.name} must hold a JSON object.")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Replace path with data in one rename. A failed write leaves the old file in place.

    Parallel All-TA coins hit the same prefs files; retry Windows Access Denied on replace.
    Locks are per-path so ``scan_progress.json`` cannot stall catalog timing writes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _lock_for(path)
    last_err: OSError | None = None
    payload = json.dumps(data, indent=2, sort_keys=True)
    for attempt in range(_REPLACE_TRIES):
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            with lock:
                os.replace(tmp_name, path)
            return
        except OSError as exc:
            last_err = exc
            Path(tmp_name).unlink(missing_ok=True)
            time.sleep(0.02 * (attempt + 1))
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
    if last_err is not None:
        raise last_err
