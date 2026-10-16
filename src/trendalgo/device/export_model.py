"""Local export helpers for the device Export page (journal CSV, plan JSON, scan JSON)."""

from __future__ import annotations

import csv
import io
import json
import shutil
from pathlib import Path
from typing import Any

from trendalgo.device.profile import EXPORTS_DIR, PLAN_FILE
from trendalgo.device.stores import StoreReadError, read_snapshot, read_trades

JOURNAL_CSV_NAME = "journal-trades.csv"
PLAN_JSON_NAME = PLAN_FILE
SCAN_JSON_NAME = "scan-latest.json"


def default_export_dir(profile_root: Path) -> Path:
    return profile_root / EXPORTS_DIR


def journal_csv_text(journal_path: Path) -> tuple[str, int]:
    """CSV body and row count. Empty string when there are no trades."""
    try:
        trades = read_trades(journal_path, limit=10_000)
    except StoreReadError as exc:
        raise OSError(str(exc)) from exc
    if not trades:
        return "", 0
    fields = (
        "created_at",
        "pair",
        "side",
        "stake_usd",
        "pnl_usd",
        "signal_source",
        "rationale",
        "exchange_trade_id",
        "exchange",
        "bot_id",
    )
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in trades:
        writer.writerow({key: row.get(key, "") for key in fields})
    return buf.getvalue(), len(trades)


def plan_export_source(plan_path: Path) -> Path | None:
    return plan_path if plan_path.is_file() else None


def scan_export_dict(scanner_path: Path) -> dict[str, Any] | None:
    try:
        snap = read_snapshot(scanner_path)
    except StoreReadError as exc:
        raise OSError(str(exc)) from exc
    if snap is None:
        return None
    return snap.to_contract_dict()


def write_journal_csv(dest_dir: Path, journal_path: Path) -> Path:
    body, count = journal_csv_text(journal_path)
    if count == 0:
        raise FileNotFoundError("journal empty")
    return _write_text(dest_dir, JOURNAL_CSV_NAME, body)


def write_plan_json(dest_dir: Path, plan_path: Path) -> Path:
    source = plan_export_source(plan_path)
    if source is None:
        raise FileNotFoundError("plan missing")
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / PLAN_JSON_NAME
    shutil.copy2(source, target)
    return target


def write_scan_json(dest_dir: Path, scanner_path: Path) -> Path:
    payload = scan_export_dict(scanner_path)
    if payload is None:
        raise FileNotFoundError("scan missing")
    text = json.dumps(payload, indent=2, sort_keys=True)
    return _write_text(dest_dir, SCAN_JSON_NAME, text)


def _write_text(dest_dir: Path, name: str, body: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / name
    path.write_text(body, encoding="utf-8")
    return path
