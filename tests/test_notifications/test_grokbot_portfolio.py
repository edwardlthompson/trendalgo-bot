import pytest

from trendalgo.notifications.grokbot_filter import event_allowed
from trendalgo.notifications.grokbot_portfolio import (
    maybe_emit_snapshot,
    qualified_bases,
    snapshot_digest,
)


def test_snapshot_digest_concentration_and_left() -> None:
    overview = {
        "net_worth_usd": 1000.0,
        "holdings": [
            {"asset": "BTC", "value_usd": 550},
            {"asset": "DOGE", "value_usd": 330},
            {"asset": "USD", "value_usd": 120},
        ],
        "allocation": [
            {"asset": "BTC", "pct": 0.55},
            {"asset": "DOGE", "pct": 0.33},
            {"asset": "USD", "pct": 0.12},
        ],
    }
    digest = snapshot_digest(overview, qualified_bases([{"symbol": "BTC"}, {"pair": "ETH/USD"}]))
    assert digest["idle_stable_share"] == 0.12
    assert digest["concentration"]["top_asset"] == "BTC"
    assert "DOGE" in digest["left_qualified"]
    assert "BTC" not in digest["left_qualified"]
    assert "USD" not in digest["left_qualified"]
    assert "account_id" not in digest


def test_snapshot_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PORTFOLIO_SNAPSHOT_WEBHOOK", raising=False)
    assert maybe_emit_snapshot({"holdings": []}) is None


def test_portfolio_filter_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GROKBOT_WEBHOOK_EVENTS", "portfolio")
    assert event_allowed("portfolio_snapshot") is True
    assert event_allowed("golive_readiness") is False
