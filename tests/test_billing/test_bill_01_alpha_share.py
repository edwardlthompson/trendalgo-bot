"""BILL-01: Alpha Share excess default; Standard Share opt-in equity HWM."""

from __future__ import annotations

from typing import Any

import pytest

from trendalgo.billing.rules import (
    SHARE_ALPHA,
    SHARE_STANDARD,
    apply_monthly_rules,
    monthly_fee,
)

BILLING_START = "2026-06-01T00:00:00+00:00"
RATE = 0.05


def _trade(pnl: float, ref: str = "t1") -> dict[str, Any]:
    return {
        "exchange_trade_id": ref,
        "pair": "BTC/USD",
        "pnl_usd": pnl,
        "created_at": "2026-06-10T12:00:00+00:00",
        "exchange": "kraken",
        "bot_id": 1,
    }


@pytest.mark.parametrize(
    ("case", "net", "bh_net", "deficit", "want_fee", "want_deficit"),
    [
        # bull-beat: fee on excess only
        ("bull-beat", 200.0, 80.0, 0.0, 6.0, 0.0),  # 0.05 * (200-80)=6
        # bull-trail: positive month but behind B&H → $0 (floor must not invent a fee)
        ("bull-trail", 50.0, 120.0, 0.0, 0.0, 70.0),  # excess -70 → deficit
        # bear-profitable: B&H negative floored to 0 → fee on full net
        ("bear-profitable", 100.0, -40.0, 0.0, 5.0, 0.0),  # 0.05 * 100; floor N/A at exactly $5
        # bear-loss: $0 fee; loss adds to excess deficit
        ("bear-loss", -80.0, -20.0, 0.0, 0.0, 80.0),
        # floor interaction: small positive excess lifts to $5, not created from $0
        ("floor-lift", 40.0, 20.0, 0.0, 5.0, 0.0),  # raw 0.05*20=1 → floor $5
        ("floor-zero-excess", 30.0, 30.0, 0.0, 0.0, 0.0),
    ],
)
def test_alpha_share_table(
    case: str,
    net: float,
    bh_net: float,
    deficit: float,
    want_fee: float,
    want_deficit: float,
) -> None:
    fee, deficit_out = monthly_fee(net, deficit, RATE, bh_net=bh_net, share_class=SHARE_ALPHA)
    assert (fee, deficit_out) == (want_fee, want_deficit), case


def test_alpha_hwm_recovers_excess_deficit_before_fee() -> None:
    # Prior bull-trail left $70 excess deficit; next month excess $100 → recover then fee on $30
    fee, deficit_out = monthly_fee(150.0, 70.0, RATE, bh_net=50.0, share_class=SHARE_ALPHA)
    assert fee == 5.0  # raw 0.05*30=1.5 → floor $5
    assert deficit_out == 0.0


def test_standard_share_keeps_equity_hwm_ignores_bh() -> None:
    fee, deficit_out = monthly_fee(100.0, 0.0, RATE, bh_net=500.0, share_class=SHARE_STANDARD)
    assert fee == 5.0  # equity net, not excess
    assert deficit_out == 0.0
    fee2, d2 = monthly_fee(50.0, 80.0, RATE, bh_net=0.0, share_class=SHARE_STANDARD)
    assert (fee2, d2) == (0.0, 30.0)


def test_apply_monthly_rules_passes_bh_and_class() -> None:
    rows, result = apply_monthly_rules(
        [_trade(200.0)],
        RATE,
        deficit_usd=0.0,
        billable_from=BILLING_START,
        bh_net=80.0,
        share_class=SHARE_ALPHA,
    )
    assert result.fee_usd == 6.0
    assert result.bh_net_usd == 80.0
    assert result.excess_usd == 120.0
    assert rows[0]["license_fee_usd"] == 6.0
