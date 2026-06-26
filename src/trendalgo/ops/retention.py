"""Data retention TTL job (LS20)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def purge_old_terms_logs(db_path: Path, ttl_days: int = 365) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=ttl_days)).isoformat()
    if not db_path.is_file():
        return 0
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("DELETE FROM terms_acceptance_log WHERE accepted_at < ?", (cutoff,))
        return cur.rowcount
