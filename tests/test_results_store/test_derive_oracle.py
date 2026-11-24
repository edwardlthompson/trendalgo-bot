"""AV-G-BOT4 — derive oracle / sauce preference for Avalonia."""

from __future__ import annotations

from pathlib import Path

from trendalgo.results_store.desk_oracle_derive import derive_oracle_rule


def test_derive_oracle_empty_without_sauce(tmp_path: Path) -> None:
    result = derive_oracle_rule(tmp_path, pair="BTC/USD")
    assert result["ok"] is False
    assert result["error"] == "empty"
    assert "All-TA" in result["message"] or "oracle" in result["message"].lower()
