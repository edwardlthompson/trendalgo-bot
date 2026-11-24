"""AV-G-BOT3 — live bot cards + enable toggle."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.profile import BOTS_DB
from trendalgo.results_store.bots_ops import load_live_bot_cards, set_bot_enabled
from trendalgo.results_store.desk_export import load_bots_surface


def test_bots_surface_has_cards_key(tmp_path: Path) -> None:
    data = load_bots_surface(tmp_path)
    assert "cards" in data
    assert data["fab_label"] == "Add bot"


def test_set_bot_enabled_roundtrip(tmp_path: Path) -> None:
    from trendalgo.bots.orchestrator import BotOrchestrator

    orch = BotOrchestrator(tmp_path / BOTS_DB)
    bot_id = orch.add_bot("Alpha", "RSI", "BTC/USD")
    assert load_live_bot_cards(tmp_path)
    paused = set_bot_enabled(tmp_path, str(bot_id), enabled=False)
    assert paused["ok"] is True
    assert paused["enabled"] is False
    resumed = set_bot_enabled(tmp_path, str(bot_id), enabled=True)
    assert resumed["ok"] is True
    assert resumed["enabled"] is True
