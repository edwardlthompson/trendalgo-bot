"""Panic: halt new buys everywhere and request flatten (Phase 0; RISK-10).

Sells/flatten stay allowed (R5). Entries stay blocked until an operator resets the halt.
Cancel verification polls until the venue acknowledges; on timeout, escalate to flatten and
journal every acknowledgement with the venue order id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class _Guard(Protocol):
    def halt(self, exchange: str, reason: str) -> None: ...

    def is_halted(self, exchange: str) -> bool: ...


class _Orchestrator(Protocol):
    def list_bots(self, *, include_retired: bool = False) -> list[dict[str, Any]]: ...

    def set_enabled(self, bot_id: int, enabled: bool) -> None: ...


class _ExchangeControl(Protocol):
    def set_paused(self, exchange_id: str, paused: bool) -> None: ...

    def list_states(self) -> list[dict[str, Any]]: ...


class CancelVerifier(Protocol):
    """Venue cancel + poll contract (RISK-10)."""

    def cancel_open_orders(self, exchange: str) -> list[str]: ...

    def confirm_cancelled(
        self, exchange: str, order_ids: list[str], *, timeout_s: float
    ) -> list[str]:
        """Return order ids the venue confirmed cancelled within timeout."""
        ...

    def remaining_open(self, exchange: str) -> list[str]:
        """Open order ids still resting after a failed/partial cancel confirm."""
        ...


@dataclass(frozen=True)
class PanicResult:
    halted_exchanges: tuple[str, ...]
    paused_bots: tuple[int, ...]
    flatten_requested: tuple[str, ...]
    reason: str
    cancelled_order_ids: tuple[str, ...] = ()
    escalated_flatten: bool = False
    cancel_ack_journal: tuple[tuple[str, str], ...] = ()


@dataclass
class CancelAckJournal:
    """In-memory ack log: (exchange, venue_order_id)."""

    entries: list[tuple[str, str]] = field(default_factory=list)

    def record(self, exchange: str, order_id: str) -> None:
        self.entries.append((exchange, order_id))


def _verify_cancels(
    *,
    cancel_verifier: CancelVerifier,
    exchange_ids: list[str],
    timeout_s: float,
    ack_journal: CancelAckJournal,
) -> tuple[list[str], bool]:
    cancelled: list[str] = []
    escalate = False
    for eid in exchange_ids:
        submitted = cancel_verifier.cancel_open_orders(eid)
        confirmed = cancel_verifier.confirm_cancelled(eid, submitted, timeout_s=timeout_s)
        for order_id in confirmed:
            ack_journal.record(eid, order_id)
            cancelled.append(order_id)
        if cancel_verifier.remaining_open(eid):
            escalate = True
    return cancelled, escalate


def run_panic(
    *,
    guard: _Guard,
    orchestrator: _Orchestrator,
    exchange_control: _ExchangeControl | None = None,
    exchanges: list[str] | None = None,
    reason: str = "panic",
    post_flatten: Any | None = None,
    cancel_verifier: CancelVerifier | None = None,
    cancel_timeout_s: float = 5.0,
    cancel_ack_journal: CancelAckJournal | None = None,
) -> PanicResult:
    """Halt buys, pause bots, verify cancels (escalate flatten when cancels hang)."""
    bots = orchestrator.list_bots()
    exchange_ids = sorted({str(b.get("exchange") or "kraken") for b in bots} | set(exchanges or []))
    if not exchange_ids:
        exchange_ids = ["kraken"]
    for eid in exchange_ids:
        guard.halt(eid, reason)
        if exchange_control is not None:
            exchange_control.set_paused(eid, True)
    paused: list[int] = []
    flatten_ids: list[str] = []
    for bot in bots:
        bot_id = int(bot["id"])
        if bot.get("enabled"):
            orchestrator.set_enabled(bot_id, False)
            paused.append(bot_id)
        label = str(bot.get("label") or bot_id)
        flatten_ids.append(label)

    cancelled: list[str] = []
    escalate = False
    ack = cancel_ack_journal or CancelAckJournal()
    if cancel_verifier is not None:
        cancelled, escalate = _verify_cancels(
            cancel_verifier=cancel_verifier,
            exchange_ids=exchange_ids,
            timeout_s=cancel_timeout_s,
            ack_journal=ack,
        )

    # Always request flatten; escalated_flatten marks cancel-verify timeout (RISK-10).
    for label in flatten_ids:
        if post_flatten is not None:
            post_flatten("flatten", label)

    return PanicResult(
        halted_exchanges=tuple(exchange_ids),
        paused_bots=tuple(paused),
        flatten_requested=tuple(flatten_ids),
        reason=reason,
        cancelled_order_ids=tuple(cancelled),
        escalated_flatten=escalate,
        cancel_ack_journal=tuple(ack.entries),
    )
