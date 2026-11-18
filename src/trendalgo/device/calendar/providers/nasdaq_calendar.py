"""NASDAQ public earnings calendar — day-fetch, client filter (no API key)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from typing import Any

from trendalgo.device.calendar.model import CalendarEvent
from trendalgo.device.calendar.nasdaq_quota import NASDAQ_MIN_INTERVAL_S

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_EARNINGS_URL = "https://api.nasdaq.com/api/calendar/earnings"


def _headers() -> dict[str, str]:
    return {
        "User-Agent": _UA,
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/",
    }


def rows_to_events(rows: list[dict[str, Any]], *, day: date) -> list[CalendarEvent]:
    events: list[CalendarEvent] = []
    day_s = day.isoformat()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or row.get("ticker") or "").strip().upper()
        if not sym:
            continue
        name = str(row.get("name") or row.get("companyName") or sym).strip()
        title = f"{sym} earnings — {name}"
        events.append(
            CalendarEvent(
                id=f"nasdaq-earn-{sym}-{day_s}-{i}",
                title=title,
                date=day_s,
                displayed_date=day_s,
                coins=(sym,),
                categories=("earnings",),
                impact=None,
                popularity=None,
                source="nasdaq",
                url="",
                is_estimated=True,
            )
        )
    return events


def filter_universe(events: list[CalendarEvent], universe: set[str]) -> list[CalendarEvent]:
    allowed = {s.upper() for s in universe}
    return [e for e in events if e.coins and e.coins[0].upper() in allowed]


def fetch_earnings_day(
    day: date,
    *,
    opener: Any | None = None,
    sleep_s: float = NASDAQ_MIN_INTERVAL_S,
) -> list[CalendarEvent]:
    query = urllib.parse.urlencode({"date": day.isoformat()})
    url = f"{_EARNINGS_URL}?{query}"
    req = urllib.request.Request(url, headers=_headers(), method="GET")
    open_fn = opener or urllib.request.urlopen
    if sleep_s > 0:
        time.sleep(sleep_s)
    try:
        with open_fn(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []
    data = payload.get("data") if isinstance(payload, dict) else None
    rows = []
    if isinstance(data, dict):
        rows = data.get("rows") or []
    if not isinstance(rows, list):
        return []
    return rows_to_events([r for r in rows if isinstance(r, dict)], day=day)
