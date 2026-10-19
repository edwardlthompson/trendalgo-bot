"""Trade notify bridges into device Alerts history."""

from __future__ import annotations

from pathlib import Path

from trendalgo.botd.trade_notify import notify_fill
from trendalgo.device.scanner_alerts_store import history_for_tab, load_history


def test_notify_fill_appends_trade_alert(tmp_path: Path) -> None:
    sent = notify_fill(
        tmp_path,
        pair="BTC/USD",
        side="buy",
        amount=0.01,
        price=100.0,
        live=False,
    )
    assert sent is False
    rows = load_history(tmp_path)
    assert rows
    assert rows[0]["kind"] == "trade_alert"
    assert "BTC" in rows[0]["symbol"]
    assert history_for_tab(rows, "trades")
    assert not history_for_tab(rows, "entered")
