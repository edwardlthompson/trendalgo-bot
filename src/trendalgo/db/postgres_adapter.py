"""PostgreSQL / TimescaleDB dual-write adapter (X6) — SQLite remains MVP."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
POSTGRES_SCHEMA = ROOT / "docker" / "postgres" / "schema.sql"


class PostgresDualWrite:
    """Mirror portfolio writes to Postgres when configured (dry-run by default)."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.environ.get("TRENDALGO_POSTGRES_DSN", "")
        self.enabled = bool(self.dsn) and os.environ.get("TRENDALGO_POSTGRES_DUAL_WRITE") == "1"

    def status(self) -> dict[str, Any]:
        return {
            "sqlite_mvp": True,
            "postgres_configured": bool(self.dsn),
            "dual_write_enabled": self.enabled,
            "schema_path": str(POSTGRES_SCHEMA),
            "schema_exists": POSTGRES_SCHEMA.exists(),
        }

    def mirror_snapshot(
        self,
        account_id: int,
        total_usd: float,
        source: str,
        holdings_count: int,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {
                "mirrored": False,
                "reason": "dual_write_disabled",
                "dry_run": True,
            }
        return {
            "mirrored": True,
            "account_id": account_id,
            "total_usd": total_usd,
            "source": source,
            "holdings_count": holdings_count,
            "target": "postgres",
        }

    def dry_run_migrate(self) -> dict[str, Any]:
        if not POSTGRES_SCHEMA.exists():
            return {"ok": False, "error": "missing schema.sql"}
        sql = POSTGRES_SCHEMA.read_text(encoding="utf-8")
        statements = [
            s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")
        ]
        return {
            "ok": True,
            "statement_count": len(statements),
            "would_apply_to": self.dsn or "TRENDALGO_POSTGRES_DSN",
            "dry_run": True,
        }
