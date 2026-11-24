"""AV-G-BOT1 — publish_plan_to_host honest failures without a linked host."""

from __future__ import annotations

from pathlib import Path

from trendalgo.results_store.bots_ops import publish_plan_to_host


def test_publish_plan_needs_owner_or_host(tmp_path: Path) -> None:
    result = publish_plan_to_host(tmp_path)
    assert result["ok"] is False
    assert result["error"] in {"needs_owner", "no_host", "plan_invalid", "plan_check"}
