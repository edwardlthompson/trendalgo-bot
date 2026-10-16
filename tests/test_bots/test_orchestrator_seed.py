"""H1: the host never seeds a live bot. A fresh database starts with zero bots."""

from pathlib import Path

from trendalgo.bots.orchestrator import BotOrchestrator


def test_fresh_database_has_zero_bots_and_zero_enabled(tmp_path: Path) -> None:
    orch = BotOrchestrator(tmp_path / "bots.db")

    assert orch.list_bots() == []
    assert orch.count_enabled() == 0


def test_reopening_database_does_not_seed_a_bot(tmp_path: Path) -> None:
    db = tmp_path / "bots.db"
    BotOrchestrator(db)

    assert BotOrchestrator(db).list_bots() == []


def test_bot_exists_only_after_an_explicit_add(tmp_path: Path) -> None:
    orch = BotOrchestrator(tmp_path / "bots.db")
    orch.add_bot("Grid-1", "grid-trading", "BTC/USD")

    bots = orch.list_bots()
    assert [b["label"] for b in bots] == ["Grid-1"]
    assert orch.count_enabled() == 1
