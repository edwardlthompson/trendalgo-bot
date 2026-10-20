"""After restart, bots resume paused — no silent live resume (Phase 0)."""

from __future__ import annotations

from typing import Any, Protocol


class _Orchestrator(Protocol):
    def list_bots(self, *, include_retired: bool = False) -> list[dict[str, Any]]: ...

    def set_enabled(self, bot_id: int, enabled: bool) -> None: ...


def pause_all_bots_on_wake(orchestrator: _Orchestrator) -> list[int]:
    """Disable every enabled bot. Returns ids that were turned off."""
    paused: list[int] = []
    for bot in orchestrator.list_bots():
        if not bot.get("enabled"):
            continue
        bot_id = int(bot["id"])
        orchestrator.set_enabled(bot_id, False)
        paused.append(bot_id)
    return paused
