"""SQLite lastrowid helper for strict mypy."""

from __future__ import annotations

from sqlite3 import Cursor


def require_row_id(cur: Cursor) -> int:
    row_id = cur.lastrowid
    if row_id is None:
        msg = "sqlite insert did not return lastrowid"
        raise RuntimeError(msg)
    return int(row_id)
