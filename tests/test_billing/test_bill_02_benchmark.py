"""BILL-02: Persist benchmark refs; statements reproduce without re-query."""

from __future__ import annotations

from trendalgo.billing.statements import build_statement, statement_from_stored
from trendalgo.billing.store import BillingStore
from trendalgo.billing.venue_attribution import (
    benchmark_refs_from_fills,
    pin_benchmark_refs,
    sum_bh_net,
)


def test_benchmark_refs_pin_open_close_venue_and_sum() -> None:
    fills = [
        {
            "pair": "BTC/USD",
            "stake_usd": 1000.0,
            "period_open_px": 100.0,
            "period_close_px": 110.0,
            "venue": "kraken",
            "fill_ts": "2026-06-30T23:59:00+00:00",
        },
        {
            "pair": "ETH/USD",
            "stake_usd": 500.0,
            "period_open_px": 50.0,
            "period_close_px": 45.0,
            "venue": "kraken",
            "fill_ts": "2026-06-30T23:50:00+00:00",
        },
    ]
    refs = benchmark_refs_from_fills(fills)
    assert refs["BTC/USD"]["bh_net_usd"] == 100.0  # 10% * 1000
    assert refs["ETH/USD"]["bh_net_usd"] == -50.0
    pinned = pin_benchmark_refs(refs)
    assert pinned["BTC/USD"]["venue_mid_open"] == 100.0
    assert pinned["BTC/USD"]["venue_mid_close"] == 110.0
    assert pinned["BTC/USD"]["pinned"] is True
    assert sum_bh_net(pinned) == 50.0


def test_statement_reproduces_benchmark_from_stored_fields_only(tmp_path) -> None:
    store = BillingStore(tmp_path / "b.db")
    refs = {
        "BTC/USD": {
            "stake_usd": 1000.0,
            "venue_mid_open": 100.0,
            "venue_mid_close": 110.0,
            "bh_net_usd": 100.0,
            "venue": "kraken",
            "fill_ts": "2026-06-30T23:59:00+00:00",
            "pinned": True,
        }
    }
    store.finalize_period(
        "2026-06",
        [
            {
                "trade_ref": "t1",
                "pair": "BTC/USD",
                "gross_profit_usd": 150.0,
                "license_fee_usd": 5.0,
                "net_benefit_usd": 145.0,
                "rule_applied": "monthly_net_fee_share",
            }
        ],
        net_usd=150.0,
        fee_usd=5.0,
        deficit_out_usd=0.0,
        bh_net_usd=100.0,
        benchmark_refs=refs,
    )
    stored = store.get_period_benchmark("2026-06")
    assert stored is not None
    assert sum_bh_net(stored["benchmark_refs"]) == 100.0
    stmt = build_statement(
        "2026-06",
        {"gross_profit_usd": 150.0, "license_fee_usd": 5.0, "net_benefit_usd": 145.0},
        [],
        bh_net_usd=stored["bh_net_usd"],
        excess_usd=50.0,
        benchmark_refs=stored["benchmark_refs"],
    )
    store.upsert_statement("2026-06", stmt)
    row = store.get_statement("2026-06")
    assert row is not None
    rebuilt = statement_from_stored(row)
    assert rebuilt["bh_net_usd"] == 100.0
    assert rebuilt["benchmark_refs"]["BTC/USD"]["venue_mid_open"] == 100.0
    assert "license_fee_usd" in rebuilt
