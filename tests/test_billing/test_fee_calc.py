"""Billing fee calculation tests (M1)."""

from trendalgo.billing.engine import process_journal_trades, reconcile_fees, seed_sample_trades
from trendalgo.billing.license_gate import check_license_gate, clear_grace, start_grace_period
from trendalgo.billing.profit import license_fee_for_trade, rollup_period
from trendalgo.billing.rules import apply_fee_rules
from trendalgo.billing.statements import build_statement, sign_payload
from trendalgo.billing.store import BillingStore
from trendalgo.risk.journal import TradeJournal
from trendalgo.risk.manager import RiskManager
from trendalgo.risk.config import RiskLimits


def test_net_loss_zero_fee() -> None:
    calc = license_fee_for_trade(-50.0, 0.12)
    assert calc.license_fee_usd == 0.0
    assert calc.rule_applied == "net_loss_zero"


def test_positive_trade_fee() -> None:
    calc = license_fee_for_trade(100.0, 0.12)
    assert calc.license_fee_usd == 12.0


def test_carry_forward_and_grace(tmp_path) -> None:
    billing = BillingStore(tmp_path / "billing.db")
    journal = TradeJournal(tmp_path / "journal.db")
    risk = RiskManager(limits=RiskLimits(), wallet_usd=1000)
    seed_sample_trades(journal)
    result = process_journal_trades(billing, journal, risk)
    assert result["rollup"]["license_fee_usd"] >= 0
    enrollment = billing.enroll(0.12, "2026-06-draft-1", "uuid-test")
    assert enrollment["enrolled"] == 1
    status = start_grace_period(billing.get_license_status(), result["period"])
    billing.update_license_status(status)
    ok, _ = check_license_gate(billing.get_enrollment(), billing.get_license_status(), dry_run=False)
    assert ok
    billing.update_license_status(clear_grace(billing.get_license_status()))
    recon = reconcile_fees(billing, journal)
    assert recon["journal_count"] >= 3


def test_statement_signing() -> None:
    items = apply_fee_rules(
        [{"pnl_usd": 25, "pair": "BTC/USD", "exchange_trade_id": "t1"}],
        0.12,
    )[0]
    rollup = rollup_period(items)
    stmt = build_statement("2026-06", rollup, items)
    assert stmt["signed_hash"] == sign_payload(stmt)
