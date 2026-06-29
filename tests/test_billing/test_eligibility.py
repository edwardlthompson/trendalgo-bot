"""Billing eligibility — delayed start after first profit."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from trendalgo.billing.eligibility import (
    add_calendar_months,
    billing_is_active,
    sync_billing_eligibility,
)
from trendalgo.billing.engine import process_journal_trades
from trendalgo.billing.store import BillingStore
from trendalgo.risk.config import RiskLimits
from trendalgo.risk.journal import TradeJournal, TradeRecord
from trendalgo.risk.manager import RiskManager


def test_add_calendar_months() -> None:
    assert add_calendar_months("2026-06-15T12:00:00+00:00") == "2026-07-15T12:00:00+00:00"
    assert add_calendar_months("2026-01-31T12:00:00+00:00") == "2026-02-28T12:00:00+00:00"


def test_no_fees_during_trial_month(tmp_path) -> None:
    billing = BillingStore(tmp_path / "billing.db")
    journal = TradeJournal(tmp_path / "journal.db")
    risk = RiskManager(limits=RiskLimits(), wallet_usd=1000)
    billing.enroll(0.05, "2026-06-draft-1", "uuid-1")
    profit_at = (datetime.now(UTC) - timedelta(days=5)).replace(microsecond=0).isoformat()
    journal.append_trade(
        TradeRecord("BTC/USD", "long", 100, 50.0, "bot", "win", "win-1"),
        created_at=profit_at,
    )
    sync_billing_eligibility(billing, journal)
    enrollment = billing.get_enrollment()
    assert enrollment["first_profitable_trade_at"] == profit_at
    assert billing_is_active(enrollment) is False
    result = process_journal_trades(billing, journal, risk)
    assert result["rollup"]["license_fee_usd"] == 0.0
    assert result["billing_eligibility"]["trial_period"] is True


def test_fees_after_billing_starts(tmp_path) -> None:
    billing = BillingStore(tmp_path / "billing.db")
    journal = TradeJournal(tmp_path / "journal.db")
    risk = RiskManager(limits=RiskLimits(), wallet_usd=1000)
    billing.enroll(0.05, "2026-06-draft-1", "uuid-2")
    first_at = "2025-01-01T00:00:00+00:00"
    billing.set_billing_eligibility(first_at, first_at)
    journal.append_trade(
        TradeRecord("BTC/USD", "long", 100, 100.0, "bot", "win", "win-2"),
        created_at="2025-02-01T00:00:00+00:00",
    )
    result = process_journal_trades(billing, journal, risk)
    assert result["rollup"]["license_fee_usd"] > 0
    assert result["billing_eligibility"]["billing_active"] is True


def test_awaiting_first_profit(tmp_path) -> None:
    billing = BillingStore(tmp_path / "billing.db")
    journal = TradeJournal(tmp_path / "journal.db")
    risk = RiskManager(limits=RiskLimits(), wallet_usd=1000)
    journal.append_trade(TradeRecord("BTC/USD", "long", 100, -10.0, "bot", "loss", "loss-1"))
    sync_billing_eligibility(billing, journal)
    assert billing.get_enrollment().get("first_profitable_trade_at") is None
    result = process_journal_trades(billing, journal, risk)
    assert result["billing_eligibility"]["awaiting_first_profit"] is True
    assert result["rollup"]["license_fee_usd"] == 0.0
