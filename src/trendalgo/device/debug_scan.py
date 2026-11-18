"""TEMP: env-gated force-fresh Qualified scan helpers.

Remove this module + Scanner Force-fresh wiring when debug is done.
Gate: ``TRENDALGO_DEBUG_SCAN=1``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from trendalgo.device.lts_scan_model import LTS_ROWS_FILE, lts_rows_path
from trendalgo.device.profile import CANDLES_DB, db_paths

_LOG = logging.getLogger("trendalgo.device.debug_scan")

ENV_FLAG = "TRENDALGO_DEBUG_SCAN"
# Price-cache DBs used by All-TA / chart overlays (LTS shim + device candles).
_PRICE_CACHE_NAMES = ("lts_price_cache.db", "lts_price_cache.db-wal", "lts_price_cache.db-shm")


def debug_scan_enabled() -> bool:
    return os.environ.get(ENV_FLAG, "").strip().lower() in {"1", "true", "yes", "on"}


def clear_scan_caches(root: Path) -> list[str]:
    """Drop Qualified rows + OHLCV price-cache files so the next scan is live."""
    cleared: list[str] = []
    rows = lts_rows_path(root)
    if rows.is_file():
        rows.unlink()
        cleared.append(LTS_ROWS_FILE)
    candidates: list[Path] = []
    data = Path(os.environ.get("TRENDALGO_DATA_DIR", "data")).resolve()
    candidates.extend(data / name for name in _PRICE_CACHE_NAMES)
    candidates.extend(root / name for name in _PRICE_CACHE_NAMES)
    try:
        candles = db_paths(root).get("candles")
    except Exception:  # noqa: BLE001 — never block force-fresh on path lookup
        candles = None
    if candles is not None:
        candidates.append(Path(candles))
        candidates.append(Path(candles).with_name(f"{CANDLES_DB}-wal"))
        candidates.append(Path(candles).with_name(f"{CANDLES_DB}-shm"))
    for path in candidates:
        try:
            if path.is_file():
                path.unlink()
                cleared.append(path.name)
        except OSError:
            continue
    # Force next All-TA load to ignore any residual cache age.
    os.environ["CACHE_PRICE_HOURS"] = "0"
    return cleared


def log_debug_scan_publish(root: Path, *, updated_at: str | None) -> None:
    """Single obvious age line after a force-fresh publish."""
    _LOG.warning(
        "DEBUG_SCAN force-fresh published root=%s updated_at=%s",
        root,
        updated_at or "unknown",
    )
