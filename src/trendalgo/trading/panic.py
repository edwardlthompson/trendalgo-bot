"""Panic: halt new buys everywhere and request flatten (Phase 0).

Sells/flatten stay allowed (R5). Entries stay blocked until an operator resets the halt.
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class PanicResult:
    halted_exchanges: tuple[str, ...]
    paused_bots: tuple[int, ...]
    flatten_requested: tuple[str, ...]
    reason: str


def run_panic(
    *,
    guard: _Guard,
    orchestrator: _Orchestrator,
    exchange_control: _ExchangeControl | None = None,
    exchanges: list[str] | None = None,
    reason: str = "panic",
    post_flatten: Any | None = None,
) -> PanicResult:
    """Halt buys, pause all bots, optionally enqueue flatten per bot label."""
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
        if post_flatten is not None:
            post_flatten("flatten", label)
    return PanicResult(
        halted_exchanges=tuple(exchange_ids),
        paused_bots=tuple(paused),
        flatten_requested=tuple(flatten_ids),
        reason=reason,
    )
