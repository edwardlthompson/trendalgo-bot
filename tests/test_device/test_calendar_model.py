"""Calendar event normalize / filter / dedupe tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trendalgo.device.calendar.model import (
    CalendarEvent,
    CalendarFilters,
    apply_filters,
    dedupe_key,
    merge_events,
)
from trendalgo.device.portfolio_categories import cash_drag_pct, categorize_holding, category_totals


def _event(**kwargs: object) -> CalendarEvent:
    day = (datetime.now(tz=UTC).date() + timedelta(days=3)).isoformat()
    base = {
        "id": "1",
        "title": "Listing",
        "date": day,
        "displayed_date": day,
        "coins": ("BTC",),
        "categories": ("Listing",),
        "impact": 7.0,
        "popularity": 10,
        "source": "coinmarketcal",
        "url": "",
        "is_estimated": False,
    }
    base.update(kwargs)
    return CalendarEvent(**base)  # type: ignore[arg-type]


def test_dedupe_prefers_cmc_impact() -> None:
    a = _event(source="coindar", impact=None, id="a")
    b = _event(source="coinmarketcal", impact=8.0, id="b")
    merged = merge_events([[a], [b]])
    assert len(merged) == 1
    assert merged[0].impact == 8.0


def test_filter_holdings_and_horizon() -> None:
    near = _event(coins=("ETH",))
    far = _event(
        date=(datetime.now(tz=UTC).date() + timedelta(days=90)).isoformat(),
        coins=("BTC",),
        title="Far",
    )
    filters = CalendarFilters(holdings_only=True, horizon_days=30, impact_min=None)
    out = apply_filters([near, far], filters, holding_symbols={"ETH"})
    assert [e.title for e in out] == ["Listing"]
    assert dedupe_key(near).startswith("listing|")


def test_category_heuristics() -> None:
    assert categorize_holding("USDC") == "Stablecoins"
    assert categorize_holding("BTC") == "Tokens"
    rows = category_totals(
        [
            {"asset": "BTC", "value_usd": 70},
            {"asset": "USDT", "value_usd": 30},
        ]
    )
    valued = [r for r in rows if r.get("value_usd") is not None]
    assert sum(float(r["value_usd"]) for r in valued) == 100
    nft = next(r for r in rows if r["category"] == "NFTs")
    assert nft.get("status") == "untracked"
    assert (
        cash_drag_pct([{"asset": "USDT", "value_usd": 50}, {"asset": "BTC", "value_usd": 50}])
        == 50.0
    )
