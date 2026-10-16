"""Research correlation note export."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.device.portfolio_model import PortfolioOverview
from trendalgo.device.research_model import correlation_note_payload, write_correlation_note


def test_correlation_note_needs_two_holdings() -> None:
    one = PortfolioOverview(
        net_worth_usd=100.0,
        daily_pnl_usd=0.0,
        daily_pnl_pct=0.0,
        realized_usd=0.0,
        unrealized_usd=0.0,
        total_pl_usd=0.0,
        health=50,
        max_drawdown_pct=0.0,
        captured_at="2026-10-10T00:00:00+00:00",
        source="test",
        holdings=[{"asset": "BTC", "value_usd": 100.0, "pct": 1.0}],
        allocation=[],
        equity=[],
        path=Path("portfolio.db"),
    )
    assert correlation_note_payload(one) is None

    two = PortfolioOverview(
        net_worth_usd=200.0,
        daily_pnl_usd=0.0,
        daily_pnl_pct=0.0,
        realized_usd=0.0,
        unrealized_usd=0.0,
        total_pl_usd=0.0,
        health=50,
        max_drawdown_pct=0.0,
        captured_at="2026-10-10T00:00:00+00:00",
        source="test",
        holdings=[
            {"asset": "BTC", "value_usd": 120.0, "pct": 0.6},
            {"asset": "ETH", "value_usd": 80.0, "pct": 0.4},
        ],
        allocation=[],
        equity=[],
        path=Path("portfolio.db"),
    )
    payload = correlation_note_payload(two)
    assert payload is not None
    assert payload["correlation"]["assets"] == ["BTC", "ETH"]
    assert payload["suggestions"]


def test_write_correlation_note(tmp_path: Path) -> None:
    payload = {"correlation": {"assets": ["BTC", "ETH"], "matrix": [[1, 0.3], [0.3, 1]]}}
    path = write_correlation_note(tmp_path / "exports", payload)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["correlation"]["assets"] == ["BTC", "ETH"]
