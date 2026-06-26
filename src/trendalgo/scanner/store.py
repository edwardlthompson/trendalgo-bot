"""Scanner SQLite persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from trendalgo.scanner.config import ScannerSettings
from trendalgo.scanner.schema import SCANNER_SCHEMA
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class ScannerStore:
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
            conn.executescript(SCANNER_SCHEMA)
            if conn.execute("SELECT 1 FROM scanner_settings WHERE id = 1").fetchone() is None:
                conn.execute(
                    """
                    INSERT INTO scanner_settings
                    (id, interval_minutes, min_volume_usd, min_gain_pct, min_uniformity,
                     universe_filter, trendspotter_boost, updated_at)
                    VALUES (1, 60, 100000, 0.02, 0.55, 'kraken-spot', 1, ?)
                    """,
                    (_utc_now(),),
                )

    def get_settings(self) -> ScannerSettings:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM scanner_settings WHERE id = 1").fetchone()
            if row is None:
                return ScannerSettings()
            return ScannerSettings(
                interval_minutes=int(row["interval_minutes"]),
                min_volume_usd=float(row["min_volume_usd"]),
                min_gain_pct=float(row["min_gain_pct"]),
                min_uniformity=float(row["min_uniformity"]),
                universe_filter=str(row["universe_filter"]),
                trendspotter_boost=bool(row["trendspotter_boost"]),
            )

    def save_settings(self, settings: ScannerSettings) -> ScannerSettings:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE scanner_settings SET
                    interval_minutes=?, min_volume_usd=?, min_gain_pct=?,
                    min_uniformity=?, universe_filter=?, trendspotter_boost=?, updated_at=?
                WHERE id=1
                """,
                (
                    settings.interval_minutes,
                    settings.min_volume_usd,
                    settings.min_gain_pct,
                    settings.min_uniformity,
                    settings.universe_filter,
                    int(settings.trendspotter_boost),
                    _utc_now(),
                ),
            )
        return settings

    def save_snapshot(self, snapshot: QualifiedSnapshot) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO scanner_snapshots (generated_at, version) VALUES (?, ?)",
                (snapshot.generated_at.isoformat(), snapshot.version),
            )
            snap_id = int(cur.lastrowid)
            for opp in snapshot.opportunities:
                conn.execute(
                    """
                    INSERT INTO scanner_opportunities
                    (snapshot_id, rank, pair, uniformity, gain_pct, volume_score,
                     entry_signal, sparkline_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snap_id,
                        opp.rank,
                        opp.pair,
                        opp.uniformity,
                        opp.gain_pct,
                        opp.volume_score,
                        int(opp.entry_signal),
                        json.dumps(opp.sparkline),
                    ),
                )
            return snap_id

    def latest_snapshot(self) -> QualifiedSnapshot | None:
        with self._connect() as conn:
            snap = conn.execute(
                "SELECT id, generated_at, version FROM scanner_snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if snap is None:
                return None
            rows = conn.execute(
                """
                SELECT rank, pair, uniformity, gain_pct, volume_score, entry_signal, sparkline_json
                FROM scanner_opportunities WHERE snapshot_id = ? ORDER BY rank
                """,
                (int(snap["id"]),),
            ).fetchall()
            opps = [
                OpportunityRow(
                    rank=int(r["rank"]),
                    pair=r["pair"],
                    uniformity=float(r["uniformity"]),
                    gain_pct=float(r["gain_pct"]),
                    volume_score=float(r["volume_score"]),
                    entry_signal=bool(r["entry_signal"]),
                    sparkline=json.loads(r["sparkline_json"]),
                )
                for r in rows
            ]
            return QualifiedSnapshot(
                version=str(snap["version"]),
                generated_at=datetime.fromisoformat(snap["generated_at"]),
                scan_id=int(snap["id"]),
                opportunities=opps,
            )

    def pin_pair(self, pair: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scanner_watchlist (pair, pinned_at) VALUES (?, ?)",
                (pair, _utc_now()),
            )

    def watchlist(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT pair FROM scanner_watchlist ORDER BY pinned_at DESC"
            ).fetchall()
            return [str(r["pair"]) for r in rows]

    def log_alert(self, tier: str, pair: str, message: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO scanner_alerts (tier, pair, message, created_at) VALUES (?, ?, ?, ?)",
                (tier, pair, message, _utc_now()),
            )
