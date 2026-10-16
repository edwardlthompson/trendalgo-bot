"""Export model: journal CSV, plan copy, scan JSON."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trendalgo.device.export_model import (
    journal_csv_text,
    write_journal_csv,
    write_plan_json,
    write_scan_json,
)
from trendalgo.device.profile import write_json
from trendalgo.risk.journal import TradeJournal, TradeRecord
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore


def _snapshot() -> QualifiedSnapshot:
    now = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
    return QualifiedSnapshot(
        generated_at=now,
        as_of=now,
        scan_id=7,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="BTC/USD",
                uniformity=0.8,
                gain_pct=1.0,
                volume_score=5.0,
                entry_signal=True,
            )
        ],
    )


def test_journal_csv_and_exports(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    journal_path = profile / "journal.db"
    journal = TradeJournal(journal_path)
    journal.append_trade(
        TradeRecord("BTC/USD", "long", 100.0, 5.0, "bot", "test", "ex-1"),
        created_at="2026-10-10T12:00:00+00:00",
    )
    body, count = journal_csv_text(journal_path)
    assert count == 1
    assert "BTC/USD" in body
    assert "created_at" in body.splitlines()[0]

    dest = profile / "exports"
    csv_path = write_journal_csv(dest, journal_path)
    assert csv_path.is_file()

    write_json(profile / "plan.json", {"version": 1, "bots": []})
    plan_path = write_plan_json(dest, profile / "plan.json")
    assert json.loads(plan_path.read_text(encoding="utf-8"))["version"] == 1

    ScannerStore(profile / "scanner.db").save_snapshot(_snapshot())
    scan_path = write_scan_json(dest, profile / "scanner.db")
    payload = json.loads(scan_path.read_text(encoding="utf-8"))
    assert payload["opportunities"][0]["pair"] == "BTC/USD"


def test_empty_journal_raises(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    journal_path = profile / "journal.db"
    TradeJournal(journal_path)
    with pytest.raises(FileNotFoundError):
        write_journal_csv(profile / "exports", journal_path)
