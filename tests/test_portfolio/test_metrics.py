from pathlib import Path

from trendalgo.portfolio.metrics import (
    allocation_rows,
    daily_pnl_from_curve,
    enrich_holdings,
    pl_breakdown,
    period_comparison,
)


def test_daily_pnl_from_curve() -> None:
    curve = [
        {"total_usd": 1000, "captured_at": "2026-06-24T00:00:00+00:00"},
        {"total_usd": 1050, "captured_at": "2026-06-25T00:00:00+00:00"},
    ]
    pnl, pct = daily_pnl_from_curve(curve)
    assert pnl == 50.0
    assert pct == 0.05


def test_pl_and_allocation() -> None:
    holdings = [
        {"asset": "BTC", "quantity": 1, "price_usd": 100, "value_usd": 100, "cost_basis_usd": 80},
    ]
    pl = pl_breakdown(holdings)
    assert pl.unrealized_usd == 20.0
    alloc = allocation_rows(holdings, 100)
    assert alloc[0]["pct"] == 1.0
    enriched = enrich_holdings(holdings)
    assert enriched[0]["unrealized_pnl_usd"] == 20.0


def test_period_comparison() -> None:
    curve = [
        {"total_usd": 900, "captured_at": "2026-05-01T00:00:00+00:00"},
        {"total_usd": 1000, "captured_at": "2026-06-25T00:00:00+00:00"},
    ]
    periods = period_comparison(curve)
    assert any(p.label == "monthly" for p in periods)
