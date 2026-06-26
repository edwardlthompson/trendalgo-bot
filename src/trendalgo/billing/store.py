"""Billing database — append-only fee ledger (M2, M13)."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trendalgo.billing.schema import BILLING_SCHEMA, CURRENT_TERMS_VERSION, DEFAULT_LICENSE_RATE


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class BillingStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _migrate(self, conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(fee_ledger_entries)").fetchall()}
        if cols and "exchange" not in cols:
            conn.execute("ALTER TABLE fee_ledger_entries ADD COLUMN exchange TEXT NOT NULL DEFAULT ''")
        if cols and "bot_id" not in cols:
            conn.execute("ALTER TABLE fee_ledger_entries ADD COLUMN bot_id INTEGER")

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(BILLING_SCHEMA)
            self._migrate(conn)
            row = conn.execute("SELECT 1 FROM license_enrollment WHERE id = 1").fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO license_enrollment
                    (id, enrolled, license_rate_pct, tier, updated_at)
                    VALUES (1, 0, ?, 'free', ?)
                    """,
                    (DEFAULT_LICENSE_RATE, _utc_now()),
                )
            status = conn.execute("SELECT 1 FROM license_status WHERE id = 1").fetchone()
            if status is None:
                conn.execute(
                    "INSERT INTO license_status (id, grace_day, suspended, updated_at) VALUES (1, 0, 0, ?)",
                    (_utc_now(),),
                )
            credit = conn.execute("SELECT 1 FROM carry_forward_credits WHERE id = 1").fetchone()
            if credit is None:
                conn.execute(
                    "INSERT INTO carry_forward_credits (id, credit_usd, updated_at) VALUES (1, 0, ?)",
                    (_utc_now(),),
                )

    def get_enrollment(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM license_enrollment WHERE id = 1").fetchone()
            return dict(row) if row else {}

    def enroll(self, rate_pct: float, terms_version: str, install_uuid: str) -> dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE license_enrollment SET
                    enrolled = 1, license_rate_pct = ?, tier = 'performance',
                    terms_version = ?, install_uuid = ?, enrolled_at = ?, updated_at = ?
                WHERE id = 1
                """,
                (rate_pct, terms_version, install_uuid, _utc_now(), _utc_now()),
            )
        return self.get_enrollment()

    def log_terms_acceptance(self, terms_version: str, install_uuid: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO terms_acceptance_log (terms_version, install_uuid, accepted_at)
                VALUES (?, ?, ?)
                """,
                (terms_version, install_uuid, _utc_now()),
            )
            return int(cur.lastrowid)

    def get_or_create_install_uuid(self) -> str:
        enrollment = self.get_enrollment()
        if enrollment.get("install_uuid"):
            return str(enrollment["install_uuid"])
        new_uuid = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "UPDATE license_enrollment SET install_uuid = ?, updated_at = ? WHERE id = 1",
                (new_uuid, _utc_now()),
            )
        return new_uuid

    def append_ledger_entry(
        self,
        trade_ref: str,
        period: str,
        pair: str,
        gross_profit_usd: float,
        license_fee_usd: float,
        net_benefit_usd: float,
        rule_applied: str,
        *,
        exchange: str = "",
        bot_id: int | None = None,
    ) -> bool:
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO fee_ledger_entries
                    (trade_ref, period, pair, gross_profit_usd, license_fee_usd,
                     net_benefit_usd, rule_applied, exchange, bot_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trade_ref,
                        period,
                        pair,
                        gross_profit_usd,
                        license_fee_usd,
                        net_benefit_usd,
                        rule_applied,
                        exchange,
                        bot_id,
                        _utc_now(),
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def list_ledger(self, period: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
        with self._connect() as conn:
            if period:
                rows = conn.execute(
                    "SELECT * FROM fee_ledger_entries WHERE period = ? ORDER BY id DESC LIMIT ?",
                    (period, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM fee_ledger_entries ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    def upsert_statement(self, period: str, statement: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO license_statements
                (period, gross_profit_usd, license_fee_usd, carry_forward_credit_usd,
                 net_loss_note, signed_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(period) DO UPDATE SET
                    gross_profit_usd = excluded.gross_profit_usd,
                    license_fee_usd = excluded.license_fee_usd,
                    carry_forward_credit_usd = excluded.carry_forward_credit_usd,
                    net_loss_note = excluded.net_loss_note,
                    signed_hash = excluded.signed_hash,
                    created_at = excluded.created_at
                """,
                (
                    period,
                    statement["gross_profit_usd"],
                    statement["license_fee_usd"],
                    statement.get("carry_forward_credit_usd", 0),
                    statement.get("net_loss_note", ""),
                    statement["signed_hash"],
                    _utc_now(),
                ),
            )

    def get_statement(self, period: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM license_statements WHERE period = ?", (period,)).fetchone()
            if row is None:
                return None
            items = conn.execute(
                "SELECT * FROM fee_ledger_entries WHERE period = ? ORDER BY id",
                (period,),
            ).fetchall()
            return {
                **dict(row),
                "line_items": [dict(i) for i in items],
            }

    def list_statements(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT period, gross_profit_usd, license_fee_usd, signed_hash, created_at "
                "FROM license_statements ORDER BY period DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_license_status(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM license_status WHERE id = 1").fetchone()
            return dict(row) if row else {}

    def update_license_status(self, status: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE license_status SET
                    grace_started_at = ?, grace_day = ?, suspended = ?,
                    unpaid_period = ?, updated_at = ?
                WHERE id = 1
                """,
                (
                    status.get("grace_started_at"),
                    int(status.get("grace_day", 0)),
                    int(status.get("suspended", 0)),
                    status.get("unpaid_period"),
                    status.get("updated_at", _utc_now()),
                ),
            )

    def get_carry_forward_credit(self) -> float:
        with self._connect() as conn:
            row = conn.execute("SELECT credit_usd FROM carry_forward_credits WHERE id = 1").fetchone()
            return float(row["credit_usd"]) if row else 0.0

    def set_carry_forward_credit(self, credit_usd: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE carry_forward_credits SET credit_usd = ?, updated_at = ? WHERE id = 1",
                (credit_usd, _utc_now()),
            )

    def record_milestone(self, milestone_usd: float) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO billing_milestones (milestone_usd, reached_at, notified) VALUES (?, ?, 1)",
                (milestone_usd, _utc_now()),
            )

    def list_milestones(self) -> list[float]:
        with self._connect() as conn:
            rows = conn.execute("SELECT milestone_usd FROM billing_milestones").fetchall()
            return [float(r["milestone_usd"]) for r in rows]

    def lifetime_totals(self) -> dict[str, float]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(gross_profit_usd), 0) AS gross,
                    COALESCE(SUM(license_fee_usd), 0) AS fees,
                    COALESCE(SUM(net_benefit_usd), 0) AS net
                FROM fee_ledger_entries
                """
            ).fetchone()
            return {
                "lifetime_gross_profit_usd": round(float(row["gross"]), 2),
                "lifetime_license_fees_usd": round(float(row["fees"]), 2),
                "lifetime_net_benefit_usd": round(float(row["net"]), 2),
            }

    def current_terms_version(self) -> str:
        return CURRENT_TERMS_VERSION
