"""Bots performance / journal / panic surfaces (AV-P1f)."""

from __future__ import annotations

from pathlib import Path

from trendalgo.results_store.bots_ops import (
    load_bots_journal_surface,
    load_bots_performance_surface,
    run_bots_panic,
)


def test_perf_and_journal_empty_without_dbs(tmp_path: Path) -> None:
    perf = load_bots_performance_surface(tmp_path)
    journal = load_bots_journal_surface(tmp_path)
    assert perf["count"] == 0
    assert journal["empty"] is True


def test_panic_without_bots_db(tmp_path: Path) -> None:
    result = run_bots_panic(tmp_path)
    assert result["ok"] is False
    assert result["error"] == "no_bots_db"
