"""Avalonia Crypto/TradFi/Forex strip → Python engine command queue (AV-G1, AUD-11).

Uses ``results.db`` ``desk_commands`` table (WAL + busy_timeout) as primary multi-process
source of truth, while syncing ``desk_commands.json`` for legacy compatibility.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from trendalgo.device.profile import read_json, write_json
from trendalgo.results_store.store import ResultsStore

COMMANDS_FILE = "desk_commands.json"

STRIP_ACTIONS = frozenset(
    {
        "run_scan",
        "run_all_scans",
        "cancel_scan",
        "open_settings",
        "run_sauce",
        "pool_watch",
        "refresh_prices",
        "share_board",
        "scan_status",
        "set_autoscan",
        "run_backtest",
        "cancel_backtest",
    }
)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _path(root: Path) -> Path:
    return root / COMMANDS_FILE


def _load_json_fallback(root: Path) -> list[dict[str, Any]]:
    data = read_json(_path(root))
    if not isinstance(data, dict):
        return []
    rows = data.get("commands")
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _row_to_dict(row: Any) -> dict[str, Any]:
    try:
        params = json.loads(str(row["params_json"] or "{}"))
    except (TypeError, ValueError):
        params = {}
    out: dict[str, Any] = {
        "id": str(row["id"]),
        "action": str(row["action"]),
        "lane": str(row["lane"]),
        "status": str(row["status"]),
        "params": params if isinstance(params, dict) else {},
    }
    detail = str(row["detail"] or "")
    if detail:
        out["detail"] = detail
    return out


def _sync_json_mirror(root: Path, store: ResultsStore) -> None:
    cur = store._conn.execute(
        "SELECT id, action, lane, status, params_json, detail FROM desk_commands ORDER BY seq ASC"
    )
    commands = [_row_to_dict(r) for r in cur.fetchall()]
    write_json(_path(root), {"commands": commands})


def _migrate_json_if_needed(root: Path, store: ResultsStore) -> None:
    count = int(store._conn.execute("SELECT COUNT(*) AS n FROM desk_commands").fetchone()["n"])
    if count > 0 or not _path(root).is_file():
        return
    now = _now()
    for item in _load_json_fallback(root):
        cid = str(item.get("id") or uuid4().hex)
        action = str(item.get("action") or "run_scan")
        lane = str(item.get("lane") or "crypto")
        status = str(item.get("status") or "pending")
        raw_params = item.get("params")
        params_json = json.dumps(raw_params if isinstance(raw_params, dict) else {})
        detail = str(item.get("detail") or "")
        store._conn.execute(
            "INSERT OR IGNORE INTO desk_commands"
            "(id, action, lane, status, params_json, detail, created_at, updated_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (cid, action, lane, status, params_json, detail, now, now),
        )
    store._conn.commit()


def enqueue_command(
    root: Path,
    action: str,
    *,
    lane: str = "crypto",
    params: dict[str, Any] | None = None,
) -> str:
    action = str(action or "").strip()
    if action not in STRIP_ACTIONS:
        raise ValueError(f"unknown desk action: {action}")
    lane_key = str(lane or "crypto").strip().lower() or "crypto"
    cmd_id = uuid4().hex
    now = _now()
    store = ResultsStore(root)
    try:
        _migrate_json_if_needed(root, store)
        if action == "cancel_scan":
            store._conn.execute(
                "UPDATE desk_commands SET status='cancelled', updated_at=? "
                "WHERE status='pending' AND action='run_scan' AND lane=?",
                (now, lane_key),
            )
        if action in {"run_scan", "run_all_scans"}:
            store._conn.execute(
                "UPDATE desk_commands SET status='superseded', "
                "detail='replaced by newer scan', updated_at=? "
                "WHERE status='pending' AND action=? AND lane=?",
                (now, action, lane_key),
            )
        store._conn.execute(
            "INSERT INTO desk_commands"
            "(id, action, lane, status, params_json, detail, created_at, updated_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (
                cmd_id,
                action,
                lane_key,
                "pending",
                json.dumps(dict(params or {}), separators=(",", ":")),
                "",
                now,
                now,
            ),
        )
        store._conn.commit()
        store.set_job_state(f"desk:{lane_key}", action, run_id=cmd_id)
        _sync_json_mirror(root, store)
    finally:
        store.close()
    return cmd_id


def peek_pending(root: Path) -> dict[str, Any] | None:
    store = ResultsStore(root)
    try:
        _migrate_json_if_needed(root, store)
        row = store._conn.execute(
            "SELECT id, action, lane, status, params_json, detail "
            "FROM desk_commands WHERE status='pending' ORDER BY seq ASC LIMIT 1"
        ).fetchone()
        return _row_to_dict(row) if row is not None else None
    finally:
        store.close()


def ack_command(
    root: Path,
    cmd_id: str,
    *,
    status: str,
    detail: str = "",
) -> None:
    now = _now()
    store = ResultsStore(root)
    try:
        _migrate_json_if_needed(root, store)
        if detail:
            store._conn.execute(
                "UPDATE desk_commands SET status=?, detail=?, updated_at=? WHERE id=?",
                (status, detail, now, cmd_id),
            )
        else:
            store._conn.execute(
                "UPDATE desk_commands SET status=?, updated_at=? WHERE id=?",
                (status, now, cmd_id),
            )
        store._conn.commit()
        row = store._conn.execute("SELECT lane FROM desk_commands WHERE id=?", (cmd_id,)).fetchone()
        lane = str(row["lane"]) if row and row["lane"] else "crypto"
        store.set_job_state(f"desk:{lane}", status, run_id=cmd_id)
        _sync_json_mirror(root, store)
    finally:
        store.close()
