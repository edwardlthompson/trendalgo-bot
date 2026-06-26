"""Portfolio sync load test (CM-6, S17)."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from trendalgo.exchanges.sync import sync_all_exchanges
from trendalgo.portfolio.db import PortfolioStore

MIN_EXCHANGES = 6
MAX_ELAPSED_SEC = 30.0


def run_load_test(*, min_exchanges: int = MIN_EXCHANGES, max_sec: float = MAX_ELAPSED_SEC) -> dict[str, object]:
    os.environ.setdefault("TRENDALGO_SYNC_STAGGER_SEC", "0")
    tmp = Path(tempfile.gettempdir()) / f"trendalgo-load-{uuid.uuid4().hex}"
    tmp.mkdir(parents=True, exist_ok=True)
    db_path = tmp / "portfolio.db"
    store = PortfolioStore(db_path)
    try:
        result = sync_all_exchanges(store, dry_run=True)
    finally:
        del store
        try:
            db_path.unlink(missing_ok=True)
            tmp.rmdir()
        except OSError:
            pass
    elapsed = float(result.get("elapsed_sec", 999))
    count = int(result.get("exchange_count", 0))
    ok = count >= min_exchanges and elapsed < max_sec
    return {
        "ok": ok,
        "exchange_count": count,
        "elapsed_sec": elapsed,
        "max_sec": max_sec,
        "min_exchanges": min_exchanges,
        "registry_version": result.get("registry_version"),
    }
