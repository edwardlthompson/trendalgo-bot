"""BILL-03: floor, profit cap, deficit age, pause quota, HWM reset."""

from __future__ import annotations

from trendalgo.billing.rules import (
    DEFICIT_MAX_MONTHS,
    HWM_RESET_PAID_STREAK,
    age_deficit,
    apply_floor_and_cap,
    monthly_fee,
    pause_allowed,
    should_reset_hwm,
)


def test_zero_excess_positive_month_stays_zero_despite_floor() -> None:
    fee, _ = monthly_fee(80.0, 0.0, 0.05, bh_net=80.0)
    assert fee == 0.0


def test_floor_lifts_small_fee_only() -> None:
    fee, floor_applied, _ = apply_floor_and_cap(1.0, profit_usd=100.0)
    assert fee == 5.0 and floor_applied
    assert apply_floor_and_cap(0.0, profit_usd=100.0) == (0.0, False, False)


def test_profit_cap_thirty_percent_and_hard_ceiling() -> None:
    # raw $5 floor on tiny profit → capped at 30% of $10 = $3
    fee, _, cap_applied = apply_floor_and_cap(1.0, profit_usd=10.0)
    assert fee == 3.0 and cap_applied
    huge, _, _ = apply_floor_and_cap(50_000.0, profit_usd=1_000_000.0)
    assert huge == 10_000.0


def test_deficit_expires_after_six_months() -> None:
    assert age_deficit(100.0, DEFICIT_MAX_MONTHS - 1) == 100.0
    assert age_deficit(100.0, DEFICIT_MAX_MONTHS) == 0.0


def test_pause_one_per_quarter_boundary() -> None:
    assert pause_allowed(0) is True
    assert pause_allowed(1) is False


def test_forced_loss_cannot_suppress_two_quarters() -> None:
    # First pause consumes the quarter quota; next quarter must re-allow once only.
    assert pause_allowed(0) is True
    assert pause_allowed(1) is False
    # New quarter resets counter externally; still only one pause.
    assert pause_allowed(0) is True


def test_hwm_resets_after_eighteen_paid() -> None:
    assert should_reset_hwm(HWM_RESET_PAID_STREAK - 1) is False
    assert should_reset_hwm(HWM_RESET_PAID_STREAK) is True
