"""Engine wiring for monthly statements: closed months, carry-forward, late trades (M7, M8)."""

from __future__ import annotations

from datetime import UTC, datetime

from trendalgo.billing.engine import process_journal_trades, reconcile_fees
from trendalgo.billing.store import BillingStore
from trendalgo.risk.config import RiskLimits
from trendalgo.risk.journal import TradeJournal, TradeRecord
from trendalgo.risk.manager import RiskManager

BILLING_START = "2025-01-01T00:00:00+00:00"


def _setup(tmp_path, *, enrolled: bool = True):
    billing = BillingStore(tmp_path / "billing.db")
    journal = TradeJournal(tmp_path / "journal.db")
    risk = RiskManager(limits=RiskLimits(), wallet_usd=1000)
    if enrolled:
        billing.enroll(0.05, "2026-06-draft-1", "uuid-monthly")
    billing.set_billing_eligibility(BILLING_START, BILLING_START)
    return billing, journal, risk


def _add(journal: TradeJournal, ref: str, pnl: float, created_at: str) -> None:
    record = TradeRecord("BTC/USD", "long", 100, pnl, "bot", "test", ref, bot_id=1)
    journal.append_trade(record, created_at=created_at)


def test_closed_month_is_finalized_once_and_a_rerun_changes_nothing(tmp_path) -> None:
    billing, journal, risk = _setup(tmp_path)
    _add(journal, "f1", 100.0, "2025-02-10T12:00:00+00:00")
    _add(journal, "f2", -40.0, "2025-02-11T12:00:00+00:00")
    first = process_journal_trades(billing, journal, risk, period="2025-02")
    assert [f["period"] for f in first["finalized"]] == ["2025-02"]
    assert first["rollup"]["license_fee_usd"] == 3.0  # net $60 at 5%
    again = process_journal_trades(billing, journal, risk, period="2025-02")
    assert again["finalized"] == []
    assert again["rollup"]["license_fee_usd"] == 3.0
    assert billing.get_carry_forward_credit() == 0.0
    assert billing.list_closed_periods() == {"2025-02": 0.0}


def test_a_loss_is_recovered_before_the_next_closed_month_pays(tmp_path) -> None:
    billing, journal, risk = _setup(tmp_path)
    _add(journal, "feb-loss", -200.0, "2025-02-10T12:00:00+00:00")
    _add(journal, "mar-win", 150.0, "2025-03-10T12:00:00+00:00")
    _add(journal, "apr-win", 100.0, "2025-04-10T12:00:00+00:00")
    result = process_journal_trades(billing, journal, risk, period="2025-03")
    assert result["rollup"]["license_fee_usd"] == 0.0
    assert billing.get_statement("2025-03")["carry_forward_credit_usd"] == 50.0
    assert billing.get_statement("2025-04")["license_fee_usd"] == 2.5
    assert billing.list_closed_periods() == {
        "2025-02": 200.0,
        "2025-03": 50.0,
        "2025-04": 0.0,
    }
    assert billing.get_carry_forward_credit() == 0.0


def test_trade_added_to_a_closed_month_is_reported_not_billed(tmp_path) -> None:
    billing, journal, risk = _setup(tmp_path)
    _add(journal, "jan-1", 100.0, "2025-01-10T12:00:00+00:00")
    process_journal_trades(billing, journal, risk, period="2025-01")
    fee_before = billing.get_statement("2025-01")["license_fee_usd"]
    _add(journal, "jan-late", 500.0, "2025-01-20T12:00:00+00:00")
    result = process_journal_trades(billing, journal, risk, period="2025-01")
    assert result["late_trades"] == ["jan-late"]
    assert billing.get_statement("2025-01")["license_fee_usd"] == fee_before
    assert "jan-late" not in {r["trade_ref"] for r in billing.list_ledger("2025-01")}
    assert reconcile_fees(billing, journal)["missing_in_ledger"] == ["jan-late"]


def test_open_month_is_provisional_and_refreshes_as_trades_arrive(tmp_path) -> None:
    billing, journal, risk = _setup(tmp_path)
    now = datetime.now(UTC).replace(microsecond=0).isoformat()
    _add(journal, "now-1", 100.0, now)
    first = process_journal_trades(billing, journal, risk)
    assert first["finalized"] == []
    assert first["rollup"]["license_fee_usd"] == 5.0
    _add(journal, "now-2", 100.0, now)
    second = process_journal_trades(billing, journal, risk)
    assert second["trades_processed"] == 1
    assert second["rollup"]["license_fee_usd"] == 10.0
    assert billing.list_closed_periods() == {}


def test_breaker_pause_waives_the_fee_of_a_month_closed_while_paused(tmp_path) -> None:
    billing, journal, risk = _setup(tmp_path)
    _add(journal, "paused", 100.0, "2025-02-10T12:00:00+00:00")
    risk.state.circuit_breaker_active = True
    result = process_journal_trades(billing, journal, risk, period="2025-02")
    assert result["rollup"]["license_fee_usd"] == 0.0
    assert billing.get_statement("2025-02")["license_fee_usd"] == 0.0


def test_enrolled_fee_opens_a_thirty_day_grace_at_day_zero(tmp_path) -> None:
    billing, journal, risk = _setup(tmp_path)
    _add(journal, "grace-1", 100.0, "2025-02-10T12:00:00+00:00")
    process_journal_trades(billing, journal, risk, period="2025-02")
    status = billing.get_license_status()
    assert status["grace_started_at"] is not None
    assert status["grace_day"] == 0
    assert status["unpaid_period"] == "2025-02"


def test_a_host_that_is_not_enrolled_is_never_put_in_grace(tmp_path) -> None:
    billing, journal, risk = _setup(tmp_path, enrolled=False)
    _add(journal, "owner-1", 100.0, "2025-02-10T12:00:00+00:00")
    result = process_journal_trades(billing, journal, risk, period="2025-02")
    assert result["rollup"]["license_fee_usd"] == 5.0  # the statement still computes
    assert billing.get_license_status().get("grace_started_at") is None
