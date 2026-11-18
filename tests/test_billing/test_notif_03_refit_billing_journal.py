"""NOTIF-03: re-fit events timestamped in billing journal."""

from __future__ import annotations

from pathlib import Path

from trendalgo.billing.refit_journal import RefitBillingJournal


def test_refit_events_timestamped_regardless_of_delivery(tmp_path: Path) -> None:
    journal = RefitBillingJournal(tmp_path / "billing.db")
    row_id = journal.append_event(
        event="refit_promoted",
        payload={"margin": 0.05, "shadow_pnl": 1.2},
        delivered=False,
    )
    assert row_id > 0
    rows = journal.list_events()
    assert len(rows) == 1
    assert rows[0]["event"] == "refit_promoted"
    assert rows[0]["delivered"] == 0
    assert rows[0]["created_at"]
    assert "margin" in rows[0]["payload_json"]
