"""Additional billing coverage."""

from pathlib import Path

from trendalgo.billing.lightning import create_lightning_invoice
from trendalgo.billing.milestones import detect_milestones
from trendalgo.billing.scheduler import run_grace_reminders, run_monthly_statement_job
from trendalgo.billing.settlement import settlement_info
from trendalgo.billing.statements import export_statement_json
from trendalgo.billing.store import BillingStore
from trendalgo.ops.retention import purge_old_terms_logs
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.risk.config import RiskLimits
from trendalgo.risk.journal import TradeJournal
from trendalgo.risk.manager import RiskManager


def test_settlement_and_lightning() -> None:
    info = settlement_info(12.5, "2026-06")
    assert info["user_initiated_only"] and not info["auto_withdraw"]
    invoice = create_lightning_invoice(10.0, "2026-06")
    assert invoice["invoice"].startswith("lnbc")


def test_milestones_and_retention(tmp_path: Path) -> None:
    hits = detect_milestones(500.0, [100])
    assert hits and hits[0]["celebrate_pnl_not_fee"]
    billing = BillingStore(tmp_path / "billing.db")
    billing.log_terms_acceptance("v1", "uuid-1")
    purged = purge_old_terms_logs(tmp_path / "billing.db", ttl_days=0)
    assert purged >= 0


def test_scheduler_jobs(tmp_path: Path) -> None:
    billing = BillingStore(tmp_path / "billing.db")
    journal = TradeJournal(tmp_path / "journal.db")
    portfolio = PortfolioStore(tmp_path / "portfolio.db")
    risk = RiskManager(limits=RiskLimits(), wallet_usd=1000)
    from trendalgo.billing.engine import seed_sample_trades

    seed_sample_trades(journal)
    run_monthly_statement_job(billing, journal, risk, portfolio)
    billing.update_license_status(
        {
            **billing.get_license_status(),
            "grace_started_at": "2026-06-01T00:00:00+00:00",
            "grace_day": 0,
            "suspended": 0,
            "unpaid_period": "2026-06",
            "updated_at": "2026-06-01T00:00:00+00:00",
        }
    )
    reminders = run_grace_reminders(billing, portfolio)
    assert reminders["grace_day"] >= 1
    stmt = billing.get_statement("2026-06")
    if stmt:
        assert export_statement_json(stmt).startswith("{")
