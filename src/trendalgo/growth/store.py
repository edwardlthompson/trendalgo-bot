"""Anonymous growth — referral + leaderboard (G1, G2)."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


GROWTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS referral_codes (
    install_uuid TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leaderboard_opt_in (
    install_uuid TEXT PRIMARY KEY,
    pseudonym TEXT NOT NULL,
    score_usd REAL NOT NULL DEFAULT 0,
    opted_in INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);
"""


def pseudonymous_code(install_uuid: str) -> str:
    return hashlib.sha256(install_uuid.encode()).hexdigest()[:10].upper()


def pseudonym_from_uuid(install_uuid: str) -> str:
    return f"trader-{hashlib.sha256(install_uuid.encode()).hexdigest()[:6]}"


class GrowthStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(GROWTH_SCHEMA)

    def get_or_create_referral(self, install_uuid: str) -> dict[str, str]:
        code = pseudonymous_code(install_uuid)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT code FROM referral_codes WHERE install_uuid = ?",
                (install_uuid,),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO referral_codes (install_uuid, code, created_at) VALUES (?, ?, ?)",
                    (install_uuid, code, _utc_now()),
                )
            else:
                code = str(row[0])
        return {"code": code, "install_uuid": install_uuid, "pseudonymous_only": True}

    def opt_in_leaderboard(self, install_uuid: str, score_usd: float) -> dict[str, Any]:
        pseudonym = pseudonym_from_uuid(install_uuid)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO leaderboard_opt_in (install_uuid, pseudonym, score_usd, opted_in, updated_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(install_uuid) DO UPDATE SET
                    score_usd = excluded.score_usd,
                    opted_in = 1,
                    updated_at = excluded.updated_at
                """,
                (install_uuid, pseudonym, score_usd, _utc_now()),
            )
        return {"pseudonym": pseudonym, "score_usd": score_usd, "opted_in": True}

    def opt_out_leaderboard(self, install_uuid: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE leaderboard_opt_in SET opted_in = 0, updated_at = ? WHERE install_uuid = ?",
                (_utc_now(), install_uuid),
            )

    def leaderboard_rows(self, limit: int = 20) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT pseudonym, score_usd, updated_at FROM leaderboard_opt_in
                WHERE opted_in = 1 ORDER BY score_usd DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                {
                    "pseudonym": r["pseudonym"],
                    "score_usd": float(r["score_usd"]),
                    "updated_at": r["updated_at"],
                }
                for r in rows
            ]
