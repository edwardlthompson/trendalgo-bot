"""Keyless macro calendar provider (biquote-style) for Forex Events."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

from trendalgo.device.calendar.model import CalendarEvent

_MACRO_URL = "https://biquote.io/api/calendar"
_CACHE_MIN_AGE_S = 6 * 3600


def cache_min_age_s() -> float:
    return float(_CACHE_MIN_AGE_S)


def rows_to_events(rows: list[dict[str, Any]]) -> list[CalendarEvent]:
    events: list[CalendarEvent] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("title") or "").strip()
        if not name:
            continue
        ts = str(row.get("time") or row.get("date") or "")[:19]
        day = ts[:10] if len(ts) >= 10 else datetime.now(UTC).strftime("%Y-%m-%d")
        ccy = str(row.get("currency") or row.get("countryCode") or "USD").upper()
        events.append(
            CalendarEvent(
                id=f"macro-{day}-{i}-{name[:24]}",
                title=name,
                date=day,
                displayed_date=day,
                coins=(ccy,),
                categories=("macro",),
                impact=None,
                popularity=None,
                source="macro",
                url="",
                is_estimated=False,
            )
        )
    return events


def fetch_macro_events(
    *,
    countries: str = "US",
    importance: str = "high",
    ahead_days: int = 7,
    opener: Any | None = None,
) -> list[CalendarEvent]:
    now = datetime.now(UTC)
    start = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    end = (now + timedelta(days=ahead_days)).strftime("%Y-%m-%d")
    query = urllib.parse.urlencode(
        {
            "countries": countries,
            "importance": importance,
            "from": start,
            "to": end,
        }
    )
    url = f"{_MACRO_URL}?{query}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "TrendAlgoDevice/1.0"},
        method="GET",
    )
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []
    rows = payload if isinstance(payload, list) else []
    if isinstance(payload, dict):
        rows = payload.get("events") or payload.get("data") or []
    if not isinstance(rows, list):
        return []
    return rows_to_events([r for r in rows if isinstance(r, dict)])
