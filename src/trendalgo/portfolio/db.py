"""Portfolio database access."""

from __future__ import annotations

import csv
import io
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.portfolio.schema import PORTFOLIO_SCHEMA


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class HoldingRow:
    asset: str
    quantity: float
    price_usd: float
    value_usd: float
    cost_basis_usd: float = 0.0


class PortfolioStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(PORTFOLIO_SCHEMA)
            try:
                conn.execute(
                    "ALTER TABLE portfolio_holdings ADD COLUMN cost_basis_usd REAL NOT NULL DEFAULT 0"
                )
            except sqlite3.OperationalError:
                pass
            row = conn.execute("SELECT 1 FROM notification_preferences WHERE id = 1").fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO notification_preferences
                    (id, trades, pnl_swings, fees, scanner, push_enabled, updated_at)
                    VALUES (1, 1, 1, 1, 0, 0, ?)
                    """,
                    (_utc_now(),),
                )
            goal = conn.execute("SELECT 1 FROM performance_goals WHERE id = 1").fetchone()
            if goal is None:
                conn.execute(
                    """
                    INSERT INTO performance_goals (id, target_net_worth_usd, deadline, label, updated_at)
                    VALUES (1, 2000, NULL, 'Growth goal', ?)
                    """,
                    (_utc_now(),),
                )

    def get_or_create_account(self, exchange: str, label: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM portfolio_accounts WHERE exchange = ? AND label = ?",
                (exchange, label),
            ).fetchone()
            if row:
                return int(row["id"])
            cur = conn.execute(
                "INSERT INTO portfolio_accounts (exchange, label, created_at) VALUES (?, ?, ?)",
                (exchange, label, _utc_now()),
            )
            return int(cur.lastrowid)

    def insert_snapshot(
        self,
        account_id: int,
        total_usd: float,
        holdings: list[HoldingRow],
        *,
        source: str,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO portfolio_snapshots (account_id, captured_at, total_usd, source)
                VALUES (?, ?, ?, ?)
                """,
                (account_id, _utc_now(), total_usd, source),
            )
            snapshot_id = int(cur.lastrowid)
            for h in holdings:
                conn.execute(
                    """
                    INSERT INTO portfolio_holdings
                    (snapshot_id, asset, quantity, price_usd, value_usd, cost_basis_usd)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        h.asset,
                        h.quantity,
                        h.price_usd,
                        h.value_usd,
                        h.cost_basis_usd,
                    ),
                )
            return snapshot_id

    def _holdings_for_snapshot(
        self, conn: sqlite3.Connection, snapshot_id: int
    ) -> list[dict[str, float | str]]:
        rows = conn.execute(
            """
            SELECT asset, quantity, price_usd, value_usd, cost_basis_usd
            FROM portfolio_holdings WHERE snapshot_id = ?
            """,
            (snapshot_id,),
        ).fetchall()
        return [
            {
                "asset": r["asset"],
                "quantity": float(r["quantity"]),
                "price_usd": float(r["price_usd"]),
                "value_usd": float(r["value_usd"]),
                "cost_basis_usd": float(r["cost_basis_usd"]),
            }
            for r in rows
        ]

    def latest_snapshot(self, account_id: int) -> dict[str, object] | None:
        with self._connect() as conn:
            snap = conn.execute(
                """
                SELECT id, captured_at, total_usd, source FROM portfolio_snapshots
                WHERE account_id = ? ORDER BY id DESC LIMIT 1
                """,
                (account_id,),
            ).fetchone()
            if snap is None:
                return None
            return {
                "snapshot_id": int(snap["id"]),
                "captured_at": snap["captured_at"],
                "total_usd": float(snap["total_usd"]),
                "source": snap["source"],
                "holdings": self._holdings_for_snapshot(conn, int(snap["id"])),
            }

    def list_snapshots(self, account_id: int, limit: int = 90) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, captured_at, total_usd, source FROM portfolio_snapshots
                WHERE account_id = ? ORDER BY id DESC LIMIT ?
                """,
                (account_id, limit),
            ).fetchall()
            return [
                {
                    "snapshot_id": int(r["id"]),
                    "captured_at": r["captured_at"],
                    "total_usd": float(r["total_usd"]),
                    "source": r["source"],
                }
                for r in rows
            ]

    def snapshot_by_date(self, account_id: int, date: str) -> dict[str, object] | None:
        with self._connect() as conn:
            snap = conn.execute(
                """
                SELECT id, captured_at, total_usd, source FROM portfolio_snapshots
                WHERE account_id = ? AND captured_at LIKE ?
                ORDER BY id DESC LIMIT 1
                """,
                (account_id, f"{date}%"),
            ).fetchone()
            if snap is None:
                return None
            return {
                "snapshot_id": int(snap["id"]),
                "captured_at": snap["captured_at"],
                "total_usd": float(snap["total_usd"]),
                "source": snap["source"],
                "holdings": self._holdings_for_snapshot(conn, int(snap["id"])),
            }

    def equity_curve(self, account_id: int, limit: int = 90) -> list[dict[str, object]]:
        snaps = self.list_snapshots(account_id, limit=limit)
        snaps.reverse()
        curve: list[dict[str, object]] = []
        for s in snaps:
            ts = datetime.fromisoformat(str(s["captured_at"]).replace("Z", "+00:00"))
            curve.append(
                {
                    "time": int(ts.timestamp()),
                    "total_usd": s["total_usd"],
                    "captured_at": s["captured_at"],
                }
            )
        return curve

    def upsert_daily_aggregate(
        self,
        account_id: int,
        date: str,
        total_usd: float,
        daily_pnl_usd: float,
        realized_pnl_usd: float,
        unrealized_pnl_usd: float,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO portfolio_daily_aggregates
                (account_id, date, total_usd, daily_pnl_usd, realized_pnl_usd, unrealized_pnl_usd)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, date) DO UPDATE SET
                    total_usd=excluded.total_usd,
                    daily_pnl_usd=excluded.daily_pnl_usd,
                    realized_pnl_usd=excluded.realized_pnl_usd,
                    unrealized_pnl_usd=excluded.unrealized_pnl_usd
                """,
                (account_id, date, total_usd, daily_pnl_usd, realized_pnl_usd, unrealized_pnl_usd),
            )

    def list_daily_aggregates(
        self, account_id: int, limit: int = 365
    ) -> list[dict[str, float | str]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT date, total_usd, daily_pnl_usd, realized_pnl_usd, unrealized_pnl_usd
                FROM portfolio_daily_aggregates
                WHERE account_id = ? ORDER BY date DESC LIMIT ?
                """,
                (account_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_snapshot_dates(self, account_id: int, limit: int = 90) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT substr(captured_at, 1, 10) AS d FROM portfolio_snapshots
                WHERE account_id = ? ORDER BY d DESC LIMIT ?
                """,
                (account_id, limit),
            ).fetchall()
            return [str(r["d"]) for r in rows]

    def insert_notification(self, category: str, title: str, body: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO notification_inbox (category, title, body, created_at, read)
                VALUES (?, ?, ?, ?, 0)
                """,
                (category, title, body, _utc_now()),
            )
            return int(cur.lastrowid)

    def list_notifications(self, limit: int = 50) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, category, title, body, created_at, read
                FROM notification_inbox ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                {
                    "id": int(r["id"]),
                    "category": r["category"],
                    "title": r["title"],
                    "body": r["body"],
                    "created_at": r["created_at"],
                    "read": bool(r["read"]),
                }
                for r in rows
            ]

    def export_holdings_csv(self, account_id: int) -> str:
        snap = self.latest_snapshot(account_id)
        if not snap:
            return "asset,quantity,price_usd,value_usd,cost_basis_usd\n"
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["asset", "quantity", "price_usd", "value_usd", "cost_basis_usd"])
        for h in snap["holdings"]:
            writer.writerow(
                [h["asset"], h["quantity"], h["price_usd"], h["value_usd"], h["cost_basis_usd"]]
            )
        return buf.getvalue()

    def get_notification_preferences(self) -> dict[str, object]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM notification_preferences WHERE id = 1").fetchone()
            if row is None:
                return {}
            return dict(row)

    def update_notification_preferences(self, prefs: dict[str, object]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE notification_preferences SET
                    trades = ?, pnl_swings = ?, fees = ?, scanner = ?,
                    push_enabled = ?, quiet_hours_start = ?, quiet_hours_end = ?, updated_at = ?
                WHERE id = 1
                """,
                (
                    int(prefs.get("trades", 1)),
                    int(prefs.get("pnl_swings", 1)),
                    int(prefs.get("fees", 1)),
                    int(prefs.get("scanner", 0)),
                    int(prefs.get("push_enabled", 0)),
                    prefs.get("quiet_hours_start"),
                    prefs.get("quiet_hours_end"),
                    _utc_now(),
                ),
            )

    def insert_webhook_audit(
        self,
        *,
        client_ip: str,
        payload_hash: str,
        accepted: bool,
        reason: str,
        source: str = "tradingview",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO webhook_audit (source, client_ip, payload_hash, accepted, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source, client_ip, payload_hash, int(accepted), reason, _utc_now()),
            )

    def list_accounts(self) -> list[dict[str, str | int]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, exchange, label, created_at FROM portfolio_accounts ORDER BY id"
            ).fetchall()
            return [
                {
                    "id": int(r["id"]),
                    "exchange": r["exchange"],
                    "label": r["label"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def set_account_meta(self, account_id: int, account_type: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO portfolio_accounts_meta (account_id, account_type)
                VALUES (?, ?)
                ON CONFLICT(account_id) DO UPDATE SET account_type = excluded.account_type
                """,
                (account_id, account_type),
            )

    def get_account_meta(self, account_id: int) -> dict[str, str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT account_type FROM portfolio_accounts_meta WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            if row is None:
                return {"account_type": "spot"}
            return {"account_type": str(row["account_type"])}

    def get_asset_tags(self) -> dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT asset, tag FROM asset_tags").fetchall()
            return {str(r["asset"]): str(r["tag"]) for r in rows}

    def set_asset_tag(self, asset: str, tag: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO asset_tags (asset, tag) VALUES (?, ?) ON CONFLICT(asset) DO UPDATE SET tag = excluded.tag",
                (asset, tag),
            )

    def get_manual_cost_basis(self, account_id: int, asset: str) -> float | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT cost_basis_usd FROM manual_cost_basis WHERE account_id = ? AND asset = ?",
                (account_id, asset),
            ).fetchone()
            if row is None:
                return None
            return float(row["cost_basis_usd"])

    def set_manual_cost_basis(self, account_id: int, asset: str, cost_basis_usd: float) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO manual_cost_basis (account_id, asset, cost_basis_usd)
                VALUES (?, ?, ?)
                ON CONFLICT(account_id, asset) DO UPDATE SET cost_basis_usd = excluded.cost_basis_usd
                """,
                (account_id, asset, cost_basis_usd),
            )

    def list_allocation_targets(self, account_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT asset, target_pct FROM allocation_targets WHERE account_id = ?",
                (account_id,),
            ).fetchall()
            return [{"asset": r["asset"], "target_pct": float(r["target_pct"])} for r in rows]

    def set_allocation_target(self, account_id: int, asset: str, target_pct: float) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO allocation_targets (account_id, asset, target_pct)
                VALUES (?, ?, ?)
                ON CONFLICT(account_id, asset) DO UPDATE SET target_pct = excluded.target_pct
                """,
                (account_id, asset, target_pct),
            )

    def get_performance_goal(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM performance_goals WHERE id = 1").fetchone()
            if row is None:
                now = _utc_now()
                conn.execute(
                    """
                    INSERT INTO performance_goals (id, target_net_worth_usd, deadline, label, updated_at)
                    VALUES (1, 2000, NULL, 'Growth goal', ?)
                    """,
                    (now,),
                )
                row = conn.execute("SELECT * FROM performance_goals WHERE id = 1").fetchone()
            return dict(row) if row else {}

    def update_performance_goal(
        self,
        target_net_worth_usd: float,
        label: str,
        deadline: str | None,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO performance_goals (id, target_net_worth_usd, deadline, label, updated_at)
                VALUES (1, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    target_net_worth_usd = excluded.target_net_worth_usd,
                    deadline = excluded.deadline,
                    label = excluded.label,
                    updated_at = excluded.updated_at
                """,
                (target_net_worth_usd, deadline, label, _utc_now()),
            )
            row = conn.execute("SELECT * FROM performance_goals WHERE id = 1").fetchone()
            return dict(row) if row else {}

    def get_basket_weights(self) -> dict[str, float]:
        import json

        with self._connect() as conn:
            row = conn.execute("SELECT weights_json FROM basket_allocation WHERE id = 1").fetchone()
            if row is None:
                return {}
            return {str(k): float(v) for k, v in json.loads(row["weights_json"]).items()}

    def set_basket_weights(self, weights: dict[str, float]) -> dict[str, float]:
        import json

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO basket_allocation (id, weights_json, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET weights_json = excluded.weights_json, updated_at = excluded.updated_at
                """,
                (json.dumps(weights), _utc_now()),
            )
        return self.get_basket_weights()
