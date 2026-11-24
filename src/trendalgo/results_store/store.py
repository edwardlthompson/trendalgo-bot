"""SQLite ResultsStore — progressive writes for Avalonia grids (ADR-0021)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from trendalgo.results_store.schema import DDL, RESULTS_DB, SCHEMA_VERSION


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class ResultsStore:
    """Owns profile ``results.db``. Shell reads; engine writes batches."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / RESULTS_DB
        self.root.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), timeout=5.0, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.executescript(DDL)
        self._conn.execute(
            "INSERT INTO meta(key, value) VALUES('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(SCHEMA_VERSION),),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def schema_version(self) -> int:
        row = self._conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        return int(row["value"]) if row else 0

    def start_run(
        self,
        kind: str,
        *,
        lane: str = "",
        pair: str = "",
        engine_version: str = "",
        catalog_hash: str = "",
        params: Mapping[str, Any] | None = None,
    ) -> str:
        run_id = uuid4().hex
        self._conn.execute(
            "INSERT INTO runs(run_id, kind, lane, pair, started_at, engine_version, "
            "catalog_hash, status, params_json) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                run_id,
                kind,
                lane,
                pair,
                _now(),
                engine_version,
                catalog_hash,
                "running",
                json.dumps(dict(params or {}), separators=(",", ":")),
            ),
        )
        self._conn.commit()
        return run_id

    def finish_run(self, run_id: str, *, status: str = "done") -> None:
        self._conn.execute(
            "UPDATE runs SET finished_at=?, status=? WHERE run_id=?",
            (_now(), status, run_id),
        )
        self._conn.commit()

    def append_opportunity_rows(
        self, run_id: str, rows: Sequence[Mapping[str, Any]], *, start_id: int = 0
    ) -> int:
        payload = [
            (
                run_id,
                start_id + i,
                str(r.get("pair", "")),
                json.dumps(dict(r), separators=(",", ":")),
            )
            for i, r in enumerate(rows)
        ]
        self._conn.executemany(
            "INSERT OR REPLACE INTO opportunity_rows(run_id, row_id, pair, payload_json) "
            "VALUES(?,?,?,?)",
            payload,
        )
        self._conn.commit()
        return len(payload)

    def append_strategy_rows(
        self, run_id: str, rows: Sequence[Mapping[str, Any]], *, start_id: int = 0
    ) -> int:
        payload = [
            (
                run_id,
                start_id + i,
                str(r.get("strategy_id", r.get("strategy", f"row-{start_id + i}"))),
                str(r.get("pair", "")),
                json.dumps(dict(r), separators=(",", ":")),
            )
            for i, r in enumerate(rows)
        ]
        self._conn.executemany(
            "INSERT OR REPLACE INTO strategy_rows"
            "(run_id, row_id, strategy_id, pair, payload_json) VALUES(?,?,?,?,?)",
            payload,
        )
        self._conn.commit()
        return len(payload)

    def set_job_state(self, job_id: str, state: str, *, run_id: str = "") -> None:
        self._conn.execute(
            "INSERT INTO job_control(job_id, run_id, state, updated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(job_id) DO UPDATE SET run_id=excluded.run_id, state=excluded.state, "
            "updated_at=excluded.updated_at",
            (job_id, run_id, state, _now()),
        )
        self._conn.commit()

    def job_state(self, job_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT state FROM job_control WHERE job_id=?", (job_id,)
        ).fetchone()
        return str(row["state"]) if row else None

    def count_strategy_rows(self, run_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM strategy_rows WHERE run_id=?", (run_id,)
        ).fetchone()
        return int(row["n"])

    def count_opportunity_rows(self, run_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM opportunity_rows WHERE run_id=?", (run_id,)
        ).fetchone()
        return int(row["n"])

    def iter_strategy_rows(
        self, run_id: str, *, offset: int = 0, limit: int = 200
    ) -> Iterable[dict[str, Any]]:
        cur = self._conn.execute(
            "SELECT strategy_id, pair, payload_json FROM strategy_rows "
            "WHERE run_id=? ORDER BY row_id LIMIT ? OFFSET ?",
            (run_id, limit, offset),
        )
        for row in cur:
            data = json.loads(row["payload_json"])
            data.setdefault("strategy_id", row["strategy_id"])
            data.setdefault("pair", row["pair"])
            yield data

    def migrate_opportunity_json(self, path: Path, *, lane: str = "crypto") -> str | None:
        """Import legacy ``lts_scan_rows.json`` list into a one-shot run."""
        if not path.is_file():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        rows = raw if isinstance(raw, list) else raw.get("rows", [])
        if not isinstance(rows, list) or not rows:
            return None
        run_id = self.start_run("migrate_opportunity", lane=lane, params={"source": path.name})
        batch: list[Mapping[str, Any]] = [r for r in rows if isinstance(r, Mapping)]
        self.append_opportunity_rows(run_id, batch)
        self.finish_run(run_id)
        return run_id
