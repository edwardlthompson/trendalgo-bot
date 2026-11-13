"""Clear local OHLCV price-cache files (free Refresh prices path)."""

from __future__ import annotations

import os
from pathlib import Path

_PRICE_CACHE_NAMES = ("lts_price_cache.db", "lts_price_cache.db-wal", "lts_price_cache.db-shm")


def clear_price_caches(root: Path | None = None) -> list[str]:
    """Delete SQLite price-cache files under DATA_DIR / profile root. Returns cleared names."""
    cleared: list[str] = []
    candidates: list[Path] = []
    data = Path(os.environ.get("TRENDALGO_DATA_DIR", "data")).resolve()
    candidates.extend(data / name for name in _PRICE_CACHE_NAMES)
    if root is not None:
        candidates.extend(Path(root) / name for name in _PRICE_CACHE_NAMES)
    for path in candidates:
        try:
            if path.is_file():
                path.unlink()
                cleared.append(path.name)
        except OSError:
            continue
    # Next load ignores residual max-age until process restart / prefs restore.
    os.environ["CACHE_PRICE_HOURS"] = "0"
    return cleared
