"""Billing fee calculation tests (M1, M7)."""

from trendalgo.billing.engine import process_journal_trades, reconcile_fees, seed_sample_trades
from trendalgo.billing.license_gate import check_license_gate, clear_grace, start_grace_period
from trendalgo.billing.profit import rollup_period
from trendalgo.billing.rules import apply_monthly_rules
from trendalgo.billing.statements import build_statement, sign_payload
from trendalgo.billing.store import BillingStore
from trendalgo.risk.config import RiskLimits
from trendalgo.risk.journal import TradeJournal
from trendalgo.risk.manager import RiskManager


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
    ok, _ = check_license_gate(
        billing.get_enrollment(), billing.get_license_status(), dry_run=False
    )
    assert ok
    billing.update_license_status(clear_grace(billing.get_license_status()))
    recon = reconcile_fees(billing, journal)
    assert recon["journal_count"] >= 3


def test_statement_signing() -> None:
    rows, _ = apply_monthly_rules(
        [
            {
                "pnl_usd": 25,
                "pair": "BTC/USD",
                "exchange_trade_id": "t1",
                "created_at": "2026-06-10T00:00:00+00:00",
            }
        ],
        0.12,
        deficit_usd=0.0,
        billable_from="2026-06-01T00:00:00+00:00",
    )
    rollup = rollup_period(rows)
    stmt = build_statement("2026-06", rollup, rows)
    assert stmt["signed_hash"] == sign_payload(stmt)
