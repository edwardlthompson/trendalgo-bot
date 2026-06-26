"""Tokenized public read-only dashboard (P17)."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


PUBLIC_SCHEMA = """
CREATE TABLE IF NOT EXISTS public_dashboard_shares (
    token TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
"""


class PublicDashboardStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(PUBLIC_SCHEMA)

    def create_token(self) -> str:
        raw = _utc_now() + "public-dashboard"
        token = hashlib.sha256(raw.encode()).hexdigest()[:20]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO public_dashboard_shares (token, created_at) VALUES (?, ?)",
                (token, _utc_now()),
            )
        return token

    def is_valid(self, token: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM public_dashboard_shares WHERE token = ?",
                (token,),
            ).fetchone()
            return row is not None


def public_overview_payload(overview: dict[str, Any]) -> dict[str, Any]:
    return {
        "read_only": True,
        "net_worth_usd": overview.get("net_worth_usd"),
        "daily_pnl_usd": overview.get("daily_pnl_usd"),
        "daily_pnl_pct": overview.get("daily_pnl_pct"),
        "health_score": overview.get("health_score"),
        "allocation": overview.get("allocation"),
        "equity_curve": overview.get("equity_curve"),
        "disclaimer": "Public read-only view. No trading actions available.",
    }
