"""Monthly net fee rules with a high-water mark (M7, ADR-0017 decision 4)."""

from __future__ import annotations

from typing import Any

import pytest

from trendalgo.billing.rules import apply_monthly_rules, group_by_month, monthly_fee

BILLING_START = "2026-06-01T00:00:00+00:00"


def _trade(
    ref: str,
    pnl: float,
    created_at: str = "2026-06-10T12:00:00+00:00",
) -> dict[str, Any]:
    return {
        "exchange_trade_id": ref,
        "pair": "BTC/USD",
        "pnl_usd": pnl,
        "created_at": created_at,
        "exchange": "kraken",
        "bot_id": 1,
        "signal_source": "bot",
    }


def _fees(rows: list[dict[str, Any]]) -> float:
    return round(sum(float(r["license_fee_usd"]) for r in rows), 2)


def test_register_example_pays_on_the_monthly_net_not_per_win() -> None:
    # 10 winners of $100 and 9 losers of $100: the month nets $100, so the fee is $5.
    # Per-trade billing on the same winners would have charged $50.
    trades = [_trade(f"w{i}", 100.0) for i in range(10)]
    trades += [_trade(f"l{i}", -100.0) for i in range(9)]
    rows, result = apply_monthly_rules(trades, 0.05, deficit_usd=0.0, billable_from=BILLING_START)
    assert result.net_usd == 100.0
    assert _fees(rows) == 5.0
    assert result.deficit_out_usd == 0.0


def test_losing_month_owes_nothing_and_its_loss_carries_forward() -> None:
    rows, result = apply_monthly_rules(
        [_trade("a", -200.0)], 0.05, deficit_usd=0.0, billable_from=BILLING_START
    )
    assert _fees(rows) == 0.0
    assert result.fee_usd == 0.0
    assert result.deficit_out_usd == 200.0
    assert rows[0]["rule_applied"] == "monthly_net_no_fee"


def test_high_water_mark_recovers_the_deficit_before_any_fee() -> None:
    _, march = apply_monthly_rules(
        [_trade("m", 150.0)], 0.05, deficit_usd=200.0, billable_from=BILLING_START
    )
    assert (march.fee_usd, march.deficit_out_usd) == (0.0, 50.0)
    _, april = apply_monthly_rules(
        [_trade("a", 100.0)], 0.05, deficit_usd=march.deficit_out_usd, billable_from=BILLING_START
    )
    # $50 of the $100 recovers the deficit; the fee is charged on the other $50 only.
    assert (april.fee_usd, april.deficit_out_usd) == (2.5, 0.0)


def test_monthly_fee_formula_edges() -> None:
    assert monthly_fee(0.0, 0.0, 0.05) == (0.0, 0.0)
    assert monthly_fee(-40.0, 10.0, 0.05) == (0.0, 50.0)
    assert monthly_fee(40.0, 100.0, 0.05) == (0.0, 60.0)
    with pytest.raises(ValueError):
        monthly_fee(1.0, -1.0, 0.05)


def test_fee_shares_add_up_to_the_month_fee_exactly() -> None:
    trades = [
        _trade("a", 33.33),
        _trade("b", 33.33),
        _trade("c", 33.34),
        _trade("d", -5.0),
        _trade("e", 0.01),
    ]
    rows, result = apply_monthly_rules(trades, 0.05, deficit_usd=0.0, billable_from=BILLING_START)
    assert _fees(rows) == round(result.fee_usd, 2)
    shares = {r["trade_ref"]: r["license_fee_usd"] for r in rows}
    assert shares["d"] == 0.0
    assert all(share >= 0 for share in shares.values())


def test_trades_before_billing_starts_are_not_billed_or_counted() -> None:
    before = _trade("t", 500.0, created_at="2026-06-05T00:00:00+00:00")
    after = _trade("u", 100.0, created_at="2026-06-20T00:00:00+00:00")
    rows, result = apply_monthly_rules(
        [before, after],
        0.05,
        deficit_usd=0.0,
        billable_from="2026-06-15T00:00:00+00:00",
    )
    by_ref = {r["trade_ref"]: r for r in rows}
    assert by_ref["t"]["rule_applied"] == "billing_trial_period"
    assert by_ref["t"]["license_fee_usd"] == 0.0
    assert result.net_usd == 100.0
    assert result.fee_usd == 5.0


def test_awaiting_first_profit_bills_nothing_and_carries_nothing() -> None:
    rows, result = apply_monthly_rules(
        [_trade("a", -30.0)], 0.05, deficit_usd=12.0, billable_from=None
    )
    assert rows[0]["rule_applied"] == "awaiting_first_profit"
    assert (result.net_usd, result.fee_usd, result.deficit_out_usd) == (0.0, 0.0, 12.0)


def test_drawdown_pause_waives_the_fee_but_the_deficit_still_moves() -> None:
    rows, result = apply_monthly_rules(
        [_trade("a", 300.0)],
        0.05,
        deficit_usd=100.0,
        drawdown_paused=True,
        billable_from=BILLING_START,
    )
    assert _fees(rows) == 0.0
    assert rows[0]["rule_applied"] == "drawdown_pause"
    assert (result.fee_usd, result.deficit_out_usd) == (0.0, 0.0)


def test_months_are_utc_calendar_months() -> None:
    trades = [
        _trade("late-june-utc", 1.0, created_at="2026-06-30T20:00:00+00:00"),
        _trade("local-june-30-is-utc-july", 1.0, created_at="2026-06-30T23:30:00-04:00"),
        _trade("unreadable-time", 1.0, created_at=""),
    ]
    groups = group_by_month(trades, current_period="2026-06")
    assert sorted(groups) == ["2026-06", "2026-07"]
    assert [t["exchange_trade_id"] for t in groups["2026-07"]] == ["local-june-30-is-utc-july"]
    assert "unreadable-time" in [t["exchange_trade_id"] for t in groups["2026-06"]]
