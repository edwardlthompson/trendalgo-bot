"""SQLite persistence for TA fleet backtest rankings."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.db.rowid import require_row_id

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ta_fleet_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    exchange_id TEXT NOT NULL,
    pair TEXT NOT NULL,
    stake_usd REAL NOT NULL,
    summary_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ta_fleet_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    strategy_id TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    net_profit REAL NOT NULL,
    gross_profit REAL NOT NULL,
    fees_paid REAL NOT NULL,
    trades INTEGER NOT NULL,
    bar_count INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES ta_fleet_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_fleet_results_run ON ta_fleet_results(run_id, rank);
"""


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class FleetStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_SCHEMA)

    def save_run(
        self,
        job_id: str,
        exchange_id: str,
        pair: str,
        stake_usd: float,
        summary: dict[str, Any],
        rankings: list[dict[str, Any]],
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO ta_fleet_runs (job_id, exchange_id, pair, stake_usd, summary_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, exchange_id, pair, stake_usd, json.dumps(summary), _utc_now()),
            )
            run_id = require_row_id(cur)
            rows = [
                (
                    run_id,
                    int(r.get("rank", i + 1)),
                    r["strategy_id"],
                    r["timeframe"],
                    r["net_profit"],
                    r["gross_profit"],
                    r["fees_paid"],
                    int(r["trades"]),
                    int(r["bar_count"]),
                    json.dumps(r),
                )
                for i, r in enumerate(rankings)
            ]
            conn.executemany(
                """
                INSERT INTO ta_fleet_results
                (run_id, rank, strategy_id, timeframe, net_profit, gross_profit,
                 fees_paid, trades, bar_count, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            return run_id

    def latest(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        group_by: str | None = None,
    ) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            run = conn.execute("SELECT * FROM ta_fleet_runs ORDER BY id DESC LIMIT 1").fetchone()
            if run is None:
                return None
            run_id = int(run["id"])
            summary = json.loads(run["summary_json"])
            rows = conn.execute(
                """
                SELECT payload_json FROM ta_fleet_results
                WHERE run_id = ? ORDER BY rank ASC
                """,
                (run_id,),
            ).fetchall()
        rankings = [json.loads(r["payload_json"]) for r in rows]
        if group_by == "strategy":
            from trendalgo.backtest.ta_fleet import group_by_strategy

            rankings = group_by_strategy(rankings)
        elif group_by and group_by != "all":
            from trendalgo.backtest.ta_fleet import group_by_timeframe

            rankings = group_by_timeframe(rankings, group_by)
        page = rankings[offset : offset + limit]
        return {
            "job_id": run["job_id"],
            "exchange_id": run["exchange_id"],
            "pair": run["pair"],
            "stake_usd": run["stake_usd"],
            "created_at": run["created_at"],
            "summary": summary,
            "rankings": page,
            "total_rankings": len(rankings),
            "limit": limit,
            "offset": offset,
        }

    def list_runs(self, *, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            total = int(conn.execute("SELECT COUNT(*) FROM ta_fleet_runs").fetchone()[0])
            rows = conn.execute(
                """
                SELECT job_id, exchange_id, pair, stake_usd, summary_json, created_at
                FROM ta_fleet_runs ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        runs: list[dict[str, Any]] = []
        for row in rows:
            summary = json.loads(row["summary_json"])
            final = summary.get("final_top10") or summary.get("optimized_top10") or []
            best = final[0] if final else {}
            runs.append(
                {
                    "job_id": row["job_id"],
                    "exchange_id": row["exchange_id"],
                    "pair": row["pair"],
                    "stake_usd": row["stake_usd"],
                    "created_at": row["created_at"],
                    "lookback_days": summary.get("lookback_days"),
                    "timeframes_tested": summary.get("timeframes_tested") or [],
                    "best_strategy": best.get("strategy_id"),
                    "best_net_profit": best.get("net_profit"),
                    "best_timeframe": best.get("timeframe"),
                    "buy_hold_net": (summary.get("buy_and_hold") or {}).get("net_profit"),
                    "top10_count": len(final),
                }
            )
        return {"runs": runs, "total": total, "limit": limit, "offset": offset}

    def get_run(self, job_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            run = conn.execute(
                "SELECT * FROM ta_fleet_runs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if run is None:
                return None
            run_id = int(run["id"])
            summary = json.loads(run["summary_json"])
            rows = conn.execute(
                "SELECT payload_json FROM ta_fleet_results WHERE run_id = ? ORDER BY rank ASC",
                (run_id,),
            ).fetchall()
        rankings = [json.loads(r["payload_json"]) for r in rows]
        final = summary.get("final_top10") or []
        return {
            "job_id": run["job_id"],
            "exchange_id": run["exchange_id"],
            "pair": run["pair"],
            "stake_usd": run["stake_usd"],
            "created_at": run["created_at"],
            "summary": summary,
            "rankings": rankings,
            "final_top10": final,
            "total_rankings": len(rankings),
        }
