"""Sprint 8 portfolio advanced tests."""

from trendalgo.portfolio.arbitrage import detect_arbitrage_opportunities
from trendalgo.portfolio.basket import apply_basket_to_bots, normalize_weights
from trendalgo.portfolio.comparisons import yoy_mom_comparison
from trendalgo.portfolio.goals import goal_progress
from trendalgo.portfolio.multi_exchange import aggregate_holdings, sync_all_exchanges
from trendalgo.portfolio.rebalance import rebalance_suggestions
from trendalgo.portfolio.tags import default_tag, tag_holdings
from trendalgo.api.public_dashboard import PublicDashboardStore, public_overview_payload


def test_multi_exchange_and_tags(tmp_path) -> None:
    from trendalgo.portfolio.db import PortfolioStore

    store = PortfolioStore(tmp_path / "portfolio.db")
    sync_all_exchanges(store, dry_run=True)
    agg = aggregate_holdings(store)
    assert agg["exchange_count"] >= 2
    store.set_asset_tag("BTC", "L1")
    tagged = tag_holdings([{"asset": "BTC", "value_usd": 100}], store.get_asset_tags())
    assert tagged[0]["tag"] == "L1"
    assert default_tag("ETH") == "L1"


def test_rebalance_goals_basket() -> None:
    suggestions = rebalance_suggestions(
        [{"asset": "BTC", "pct": 0.3}],
        [{"asset": "BTC", "target_pct": 0.5}],
        1000.0,
    )
    assert suggestions and suggestions[0]["action"] == "buy"
    goal = goal_progress(1500, {"target_net_worth_usd": 2000, "label": "G"})
    assert goal["progress_pct"] == 0.75
    weights = normalize_weights({"1": 60, "2": 40})
    bots = apply_basket_to_bots([{"id": 1, "label": "a", "equity_usd": 100}], weights, 1000)
    assert bots[0]["weight_pct"] == 0.6


def test_arbitrage_and_public(tmp_path) -> None:
    arb = detect_arbitrage_opportunities(dry_run=True)
    assert arb["auto_trade"] is False and arb["count"] >= 1
    store = PublicDashboardStore(tmp_path / "public.db")
    token = store.create_token()
    assert store.is_valid(token)
    payload = public_overview_payload({"net_worth_usd": 1000, "allocation": []})
    assert payload["read_only"]


def test_comparisons() -> None:
    curve = [
        {"captured_at": "2025-06-01T00:00:00+00:00", "total_usd": 1000},
        {"captured_at": "2026-06-25T00:00:00+00:00", "total_usd": 1100},
    ]
    rows = yoy_mom_comparison([], curve)
    assert any(r["label"] == "yoy" for r in rows)
