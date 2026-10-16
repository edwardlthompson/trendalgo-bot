"""Device databases (D3): WAL journal and a busy timeout, so the UI, workers, and jobs can share files."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

BUSY_TIMEOUT_S = 5.0


def connect(path: Path) -> sqlite3.Connection:
    """A connection that waits up to BUSY_TIMEOUT_S for a lock instead of failing at once."""
    conn = sqlite3.connect(path, timeout=BUSY_TIMEOUT_S)
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def enable_wal(path: Path) -> str:
    """Switch a device database to WAL; the mode sticks in the file. Returns the mode in force."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as conn:
        row = conn.execute("PRAGMA journal_mode = WAL").fetchone()
    return str(row[0]).lower()
