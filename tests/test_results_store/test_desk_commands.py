"""Desk command queue — Avalonia strip → Python engine (AV-G1)."""

from __future__ import annotations

from pathlib import Path

from trendalgo.results_store.desk_commands import (
    STRIP_ACTIONS,
    ack_command,
    enqueue_command,
    peek_pending,
)


def test_strip_actions_cover_crypto_desk() -> None:
    required = {
        "run_scan",
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
    assert required <= STRIP_ACTIONS


def test_enqueue_peek_ack_roundtrip(tmp_path: Path) -> None:
    cid = enqueue_command(tmp_path, "run_scan", lane="crypto")
    assert cid
    pending = peek_pending(tmp_path)
    assert pending is not None
    assert pending["id"] == cid
    assert pending["action"] == "run_scan"
    assert pending["lane"] == "crypto"
    assert pending["status"] == "pending"
    ack_command(tmp_path, cid, status="running")
    mid = peek_pending(tmp_path)
    assert mid is None or mid["id"] != cid or mid["status"] != "pending"
    ack_command(tmp_path, cid, status="done", detail="ok")
    done = peek_pending(tmp_path)
    assert done is None or done.get("status") != "pending"


def test_cancel_supersedes_pending_run(tmp_path: Path) -> None:
    enqueue_command(tmp_path, "run_scan", lane="crypto")
    cancel_id = enqueue_command(tmp_path, "cancel_scan", lane="crypto")
    pending = peek_pending(tmp_path)
    assert pending is not None
    assert pending["id"] == cancel_id
    assert pending["action"] == "cancel_scan"
