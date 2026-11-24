"""Execution venue settings for Avalonia Settings → Venue (AV-G-SET1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["apply_execution_venue", "load_execution_venue_surface"]


def load_execution_venue_surface(root: Path) -> dict[str, Any]:
    from trendalgo.device import strings as S
    from trendalgo.device.execution_venue import DISCLOSURE_TEXT, load_execution_venue

    settings = load_execution_venue(root)
    return {
        "venue": settings.venue,
        "disclosure_accepted": settings.disclosure_accepted,
        "first_bot_rails_lifted": settings.first_bot_rails_lifted,
        "disclosure_text": DISCLOSURE_TEXT,
        "label": S.SETTINGS_VENUE,
        "host_label": S.SETTINGS_VENUE_HOST,
        "device_label": S.SETTINGS_VENUE_DEVICE,
        "ack_label": S.SETTINGS_VENUE_ACK,
        "choices": [
            {"id": "host", "label": S.SETTINGS_VENUE_HOST},
            {"id": "device", "label": S.SETTINGS_VENUE_DEVICE},
        ],
    }


def apply_execution_venue(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    from trendalgo.device.execution_venue import (
        ExecutionVenueSettings,
        load_execution_venue,
        save_execution_venue,
    )

    current = load_execution_venue(root)
    venue = str(payload.get("venue") or current.venue).strip().lower()
    if venue not in ("host", "device"):
        return {"ok": False, "error": "bad_venue"}
    ack = bool(payload.get("disclosure_accepted")) or current.disclosure_accepted
    if venue == "device" and not ack:
        return {"ok": False, "error": "disclosure_required"}
    updated = ExecutionVenueSettings(
        venue=venue,  # type: ignore[arg-type]
        disclosure_accepted=ack if venue == "device" else current.disclosure_accepted,
        first_bot_rails_lifted=current.first_bot_rails_lifted,
    )
    save_execution_venue(root, updated)
    return {
        "ok": True,
        "venue": updated.venue,
        "disclosure_accepted": updated.disclosure_accepted,
    }
