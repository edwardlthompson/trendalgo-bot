"""PortfolioStore PRAGMA user_version migrations (HOUSE-01)."""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Callable, Sequence
from pathlib import Path

SCHEMA_VERSION = 1

MigrationFn = Callable[[sqlite3.Connection], None]

_DUPLICATE_COLUMN = "duplicate column"


def _add_column(conn: sqlite3.Connection, ddl: str) -> None:
    try:
        conn.execute(ddl)
    except sqlite3.OperationalError as exc:
        if _DUPLICATE_COLUMN in str(exc).lower():
            return
        raise


def _migrate_to_v1(conn: sqlite3.Connection) -> None:
    for ddl in (
        "ALTER TABLE portfolio_holdings ADD COLUMN cost_basis_usd REAL NOT NULL DEFAULT 0",
        "ALTER TABLE notification_inbox ADD COLUMN delivery_error TEXT",
        "ALTER TABLE performance_goals ADD COLUMN goal_type TEXT NOT NULL DEFAULT 'portfolio_growth'",
        "ALTER TABLE performance_goals ADD COLUMN horizon_months INTEGER NOT NULL DEFAULT 12",
        "ALTER TABLE performance_goals ADD COLUMN target_return_pct REAL NOT NULL DEFAULT 0",
    ):
        _add_column(conn, ddl)


MIGRATIONS: Sequence[tuple[int, MigrationFn]] = ((1, _migrate_to_v1),)


def backup_database(db_path: Path) -> Path | None:
    """Copy ``db_path`` beside itself before migrating. None when file missing."""
    if not db_path.is_file():
        return None
    backup = db_path.with_suffix(db_path.suffix + ".pre_migrate.bak")
    shutil.copy2(db_path, backup)
    return backup


def apply_migrations(conn: sqlite3.Connection, db_path: Path) -> int:
    """Run ordered migrations; backup once when any step will run. Returns final version."""
    row = conn.execute("PRAGMA user_version").fetchone()
    current = int(row[0]) if row else 0
    pending = [(ver, fn) for ver, fn in MIGRATIONS if ver > current]
    if not pending:
        return current
    backup_database(db_path)
    for ver, fn in pending:
        fn(conn)
        conn.execute(f"PRAGMA user_version = {int(ver)}")
        current = ver
    return current
