"""Execution venue preference: host (default) vs device opt-in (Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from trendalgo.device.profile import read_json, write_json

VenueChoice = Literal["host", "device"]
VENUE_FILE = "execution_venue.json"


@dataclass(frozen=True)
class ExecutionVenueSettings:
    venue: VenueChoice = "host"
    disclosure_accepted: bool = False
    first_bot_rails_lifted: bool = False


def load_execution_venue(root: Path) -> ExecutionVenueSettings:
    from trendalgo.device.profile import ProfileError

    path = root / VENUE_FILE
    try:
        raw = read_json(path)
    except ProfileError:
        return ExecutionVenueSettings()
    if not raw:
        return ExecutionVenueSettings()
    venue = raw.get("venue", "host")
    if venue not in ("host", "device"):
        venue = "host"
    return ExecutionVenueSettings(
        venue=venue,  # type: ignore[arg-type]
        disclosure_accepted=bool(raw.get("disclosure_accepted", False)),
        first_bot_rails_lifted=bool(raw.get("first_bot_rails_lifted", False)),
    )


def save_execution_venue(root: Path, settings: ExecutionVenueSettings) -> None:
    write_json(
        root / VENUE_FILE,
        {
            "venue": settings.venue,
            "disclosure_accepted": settings.disclosure_accepted,
            "first_bot_rails_lifted": settings.first_bot_rails_lifted,
        },
    )


DISCLOSURE_TEXT = (
    "Device-local live trading can miss entries or exits when this PC sleeps, "
    "reboots, loses power, or drops its ISP link. A always-on host is recommended. "
    "Checking the box means you understand and still want device execution."
)
