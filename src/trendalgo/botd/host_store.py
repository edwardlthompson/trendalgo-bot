"""Host state in one SQLite file (ADR-0016): plan, positions, outbox, heartbeat, pairing codes.

The fills ledger and the nonce store keep their own files (fills.py, signed_command.py). The
backup module snapshots every host file together.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS plan (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    plan_version INTEGER NOT NULL,
    bundle_hash TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS positions (
    bot_id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_key TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS heartbeat (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    beat_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS pairing_codes (
    code_hash TEXT PRIMARY KEY,
    expires_at INTEGER NOT NULL,
    used INTEGER NOT NULL DEFAULT 0
);
"""


class StalePlanError(ValueError):
    """A plan must carry a strictly newer plan_version than the stored one (H3)."""


class HostStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """One connection per block: commit on success, roll back on error, always close."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def save_plan(self, *, plan_version: int, bundle_hash: str, body: str) -> None:
        """Store a plan. The upsert writes only when the version is newer (atomic in SQLite)."""
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO plan (id, plan_version, bundle_hash, body) VALUES (1, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET plan_version = excluded.plan_version, "
                "bundle_hash = excluded.bundle_hash, body = excluded.body "
                "WHERE excluded.plan_version > plan.plan_version",
                (plan_version, bundle_hash, body),
            )
            if cur.rowcount == 0:
                raise StalePlanError(
                    f"plan_version {plan_version} is not newer than the stored plan"
                )

    def plan(self) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT plan_version, bundle_hash, body FROM plan WHERE id = 1"
            ).fetchone()
        return dict(row) if row is not None else None

    def save_position(self, bot_id: str, state_json: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO positions (bot_id, state_json) VALUES (?, ?) "
                "ON CONFLICT(bot_id) DO UPDATE SET state_json = excluded.state_json",
                (bot_id, state_json),
            )

    def positions(self) -> dict[str, str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT bot_id, state_json FROM positions ORDER BY bot_id"
            ).fetchall()
        return {str(row["bot_id"]): str(row["state_json"]) for row in rows}
