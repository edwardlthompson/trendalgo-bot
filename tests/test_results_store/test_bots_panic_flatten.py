"""AV-G-BOT2 — panic payload includes host flatten fields."""

from __future__ import annotations

from pathlib import Path

from trendalgo.results_store.bots_ops import run_bots_panic


def test_panic_without_bots_db(tmp_path: Path) -> None:
    result = run_bots_panic(tmp_path)
    assert result["ok"] is False
    assert result["error"] == "no_bots_db"


def test_panic_payload_has_flatten_keys(tmp_path: Path) -> None:
    # Empty orchestrator path: create minimal bots.db via BotOrchestrator if possible.
    from trendalgo.bots.orchestrator import BotOrchestrator
    from trendalgo.device.profile import BOTS_DB

    path = tmp_path / BOTS_DB
    BotOrchestrator(path)  # ensures schema
    result = run_bots_panic(tmp_path)
    assert result["ok"] is True
    assert "host_linked" in result
    assert "host_flatten_calls" in result
    assert "flatten_requested" in result
    assert result["host_linked"] is False
    assert result["host_flatten_calls"] == 0
