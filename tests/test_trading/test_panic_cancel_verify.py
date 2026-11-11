"""RISK-10: panic verifies cancels; silent drops escalate to flatten."""

from __future__ import annotations

from pathlib import Path

from trendalgo.bots.orchestrator import BotOrchestrator
from trendalgo.trading.order_journal import OrderJournal
from trendalgo.trading.panic import CancelAckJournal, run_panic


class DroppingCancelVerifier:
    """Venue silently drops cancels — confirm never sees them gone."""

    def __init__(self, open_ids: list[str]) -> None:
        self.open_ids = list(open_ids)
        self.cancel_calls = 0

    def cancel_open_orders(self, exchange: str) -> list[str]:
        self.cancel_calls += 1
        return list(self.open_ids)

    def confirm_cancelled(
        self, exchange: str, order_ids: list[str], *, timeout_s: float
    ) -> list[str]:
        return []  # never acknowledges

    def remaining_open(self, exchange: str) -> list[str]:
        return list(self.open_ids)


class AckingCancelVerifier:
    def __init__(self, open_ids: list[str]) -> None:
        self.open_ids = list(open_ids)

    def cancel_open_orders(self, exchange: str) -> list[str]:
        return list(self.open_ids)

    def confirm_cancelled(
        self, exchange: str, order_ids: list[str], *, timeout_s: float
    ) -> list[str]:
        confirmed = list(order_ids)
        self.open_ids = [oid for oid in self.open_ids if oid not in confirmed]
        return confirmed

    def remaining_open(self, exchange: str) -> list[str]:
        return list(self.open_ids)


def test_silent_cancel_drop_escalates_to_flatten(tmp_path: Path) -> None:
    orch = BotOrchestrator(tmp_path / "bots.db")
    orch.add_bot("A", "sma", "BTC/USD", equity_usd=100, enabled=True)
    journal = OrderJournal(tmp_path / "journal.db")
    flatten: list[tuple[str, str]] = []
    verifier = DroppingCancelVerifier(["ord-1", "ord-2"])
    ack = CancelAckJournal()
    result = run_panic(
        guard=journal,
        orchestrator=orch,
        post_flatten=lambda a, b: flatten.append((a, b)),
        cancel_verifier=verifier,
        cancel_ack_journal=ack,
        reason="test_panic",
    )
    assert result.escalated_flatten is True
    assert result.cancelled_order_ids == ()
    assert flatten == [("flatten", "A")]
    assert verifier.cancel_calls == 1
    assert ack.entries == []


def test_confirmed_cancels_are_journaled(tmp_path: Path) -> None:
    orch = BotOrchestrator(tmp_path / "bots.db")
    orch.add_bot("A", "sma", "BTC/USD", equity_usd=100, enabled=True)
    journal = OrderJournal(tmp_path / "journal.db")
    verifier = AckingCancelVerifier(["ord-9"])
    ack = CancelAckJournal()
    result = run_panic(
        guard=journal,
        orchestrator=orch,
        cancel_verifier=verifier,
        cancel_ack_journal=ack,
        reason="test_panic",
    )
    assert result.escalated_flatten is False
    assert result.cancelled_order_ids == ("ord-9",)
    assert ack.entries == [("kraken", "ord-9")]
