"""HOUSE-01/02: user_version migrations, backup, WAL pragmas; re-raise non-dup."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.migrations import SCHEMA_VERSION, _add_column, apply_migrations


def test_connect_sets_wal_and_busy_timeout(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "p.db")
    with store._connect() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        sync = conn.execute("PRAGMA synchronous").fetchone()[0]
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert str(mode).lower() == "wal"
    assert int(timeout) == 5000
    # NORMAL == 1
    assert int(sync) == 1
    assert int(version) == SCHEMA_VERSION


def test_migration_backs_up_and_sets_user_version(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE portfolio_holdings (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE notification_inbox (id INTEGER PRIMARY KEY)")
        conn.execute("CREATE TABLE performance_goals (id INTEGER PRIMARY KEY)")
        conn.execute("PRAGMA user_version = 0")
    with sqlite3.connect(path) as conn:
        apply_migrations(conn, path)
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert int(version) == SCHEMA_VERSION
    assert path.with_suffix(path.suffix + ".pre_migrate.bak").is_file()


def test_non_duplicate_column_reraises(tmp_path: Path) -> None:
    path = tmp_path / "bad.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE t (id INTEGER)")
        with pytest.raises(sqlite3.OperationalError):
            _add_column(conn, "ALTER TABLE missing ADD COLUMN x TEXT")
