"""Local JSON cache for calendar events."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.calendar.model import CalendarEvent, event_from_dict, event_to_dict
from trendalgo.device.profile import read_json, write_json

CACHE_FILE = "calendar_events_cache.json"


def cache_path(root: Path) -> Path:
    return root / CACHE_FILE


def load_events(root: Path) -> list[CalendarEvent]:
    raw = read_json(cache_path(root))
    if not isinstance(raw, dict):
        return []
    items = raw.get("events")
    if not isinstance(items, list):
        return []
    out: list[CalendarEvent] = []
    for item in items:
        if isinstance(item, dict):
            out.append(event_from_dict(item))
    return out


def save_events(root: Path, events: list[CalendarEvent], *, fetched_at: str) -> None:
    payload: dict[str, Any] = {
        "fetched_at": fetched_at,
        "events": [event_to_dict(e) for e in events],
    }
    write_json(cache_path(root), payload)


def fetched_at(root: Path) -> str | None:
    raw = read_json(cache_path(root))
    if isinstance(raw, dict) and isinstance(raw.get("fetched_at"), str):
        return raw["fetched_at"]
    return None
