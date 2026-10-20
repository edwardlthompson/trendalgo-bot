"""Vault / Sync / Live status lights — keys ≠ live (Phase 0)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LightState(StrEnum):
    OFF = "off"
    OK = "ok"
    WARN = "warn"
    BAD = "bad"


@dataclass(frozen=True)
class SafetyLights:
    vault: LightState
    sync: LightState
    live: LightState

    def as_dict(self) -> dict[str, str]:
        return {"vault": self.vault.value, "sync": self.sync.value, "live": self.live.value}


def compute_safety_lights(
    *,
    vault_unlocked: bool,
    has_query_key: bool,
    sync_ok: bool,
    go_live_approved: bool,
    live_requested: bool = False,
) -> SafetyLights:
    """Live stays off/bad until go-live; Sync green with query-only keys is success."""
    if not vault_unlocked:
        vault = LightState.BAD
    elif has_query_key:
        vault = LightState.OK
    else:
        vault = LightState.WARN
    if sync_ok and has_query_key:
        sync = LightState.OK
    elif has_query_key:
        sync = LightState.WARN
    else:
        sync = LightState.OFF
    if go_live_approved and live_requested:
        live = LightState.WARN  # armed — still scary
    elif go_live_approved:
        live = LightState.OK  # approved but not currently requesting live ticks
    else:
        live = LightState.OFF
    return SafetyLights(vault=vault, sync=sync, live=live)
