"""Why? callback posts explain_request even when the original event is filtered."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from trendalgo.notifications.grokbot_explain import handle_why, stash, why_markup
from trendalgo.notifications.grokbot_filter import event_allowed
from trendalgo.notifications.grokbot_payload import trade_payload


def test_explain_request_bypasses_trades_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GROKBOT_WEBHOOK_URL", "https://example.invalid/hook")
    monkeypatch.setenv("GROKBOT_WEBHOOK_EVENTS", "scanner-a")
    assert event_allowed("trade_exit") is False
    assert event_allowed("explain_request") is True
    posted: list[str] = []

    def capture(payload: dict[str, Any], **_k: Any) -> dict[str, Any]:
        posted.append(str(payload.get("event_type")))
        return {"sent": True}

    monkeypatch.setattr("trendalgo.notifications.grokbot.emit", capture)
    source = trade_payload(
        pair="BTC/USD",
        side="sell",
        amount=1,
        price=2,
        strategy_id="macd-kraken-1h",
        exit_rule="MACD cross down",
    )
    token = stash(source)
    result = handle_why(f"why:{token}")
    assert result["sent"] is True
    assert posted == ["explain_request"]


def test_why_markup_includes_callback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    markup = why_markup({"event_type": "trade_exit", "pair": "ETH/USD"})
    assert "Why?" in markup
    assert "why:" in markup
