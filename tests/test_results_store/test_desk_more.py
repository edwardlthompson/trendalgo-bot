"""Billing / About / force-fresh desk helpers."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.results_store.desk_commands import enqueue_command, peek_pending
from trendalgo.results_store.desk_more import (
    apply_force_fresh,
    load_about_surface,
    load_billing_surface,
    load_notify_surface,
)
from trendalgo.results_store.desk_worker import process_pending


def test_billing_surface_owner_only_settle_disabled() -> None:
    data = load_billing_surface()
    assert data["settle_enabled"] is False
    assert data["tier"] == "owner-only"
    assert "Settle" in data["settle_label"] or "settle" in data["settle_help"].lower()


def test_about_surface_has_version_and_changelog() -> None:
    data = load_about_surface()
    assert data["version"]
    assert "Version" in data["version_line"]
    assert "CHANGELOG" in data["changelog_url"]


def test_notify_surface_matrix_kinds(tmp_path: Path) -> None:
    data = load_notify_surface(tmp_path)
    assert len(data["kinds"]) == 4
    assert data["start_with_windows"] is True
    assert {k["id"] for k in data["kinds"]} == {"logs", "entered", "left", "trades"}


def test_force_fresh_param_clears_lts_then_publishes(tmp_path: Path) -> None:
    rows = [{"pair": "BTC/USD", "gain": 1.0, "exchange": "kraken", "volume_score": 1.0}]
    (tmp_path / "lts_scan_rows.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")
    cleared = apply_force_fresh(tmp_path)
    assert "lts_scan_rows.json" in cleared
    assert not (tmp_path / "lts_scan_rows.json").is_file()
    # Re-seed so dry desk-once can publish
    (tmp_path / "lts_scan_rows.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")
    cid = enqueue_command(tmp_path, "run_scan", lane="crypto", params={"force_fresh": True})
    pending = peek_pending(tmp_path)
    assert pending is not None
    assert pending["id"] == cid
    assert pending["params"]["force_fresh"] is True
    result = process_pending(tmp_path, dry_run=True)
    assert result is not None
    assert result["status"] == "done"
