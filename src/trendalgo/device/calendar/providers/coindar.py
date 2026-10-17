"""Coindar official API client (access_token query param)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

from trendalgo.device.calendar.model import CalendarEvent
from trendalgo.device.calendar.providers.coinmarketcal import ProviderError

BASE = "https://coindar.org/api/v2"


def test_token(token: str, *, timeout: float = 15.0) -> None:
    fetch_events(token, page_size=1, timeout=timeout)


def fetch_events(
    token: str,
    *,
    page_size: int = 50,
    timeout: float = 20.0,
) -> list[CalendarEvent]:
    start = datetime.now(tz=UTC).date().isoformat()
    end = (datetime.now(tz=UTC).date() + timedelta(days=90)).isoformat()
    query = urllib.parse.urlencode(
        {
            "access_token": token,
            "page": 1,
            "page_size": max(1, min(page_size, 100)),
            "filter_date_start": start,
            "filter_date_end": end,
            "sort_by": "views",
            "order_by": 1,
        }
    )
    url = f"{BASE}/events?{query}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"Coindar HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"Coindar unreachable: {exc.reason}") from exc
    items = payload if isinstance(payload, list) else []
    return [_normalize(item) for item in items if isinstance(item, dict)]


def _normalize(raw: dict[str, Any]) -> CalendarEvent:
    start = str(raw.get("date_start") or raw.get("date") or "")
    caption = str(raw.get("caption") or raw.get("title") or "Event")
    tags = raw.get("tags") or []
    cats = tuple(str(t) for t in tags) if isinstance(tags, list) else ()
    views = raw.get("views")
    try:
        popularity = int(views) if views is not None else None
    except (TypeError, ValueError):
        popularity = None
    coin_id = raw.get("coin_id")
    coins = (str(coin_id),) if coin_id is not None else ()
    return CalendarEvent(
        id=f"coindar:{raw.get('id') or start}:{caption}",
        title=caption,
        date=start,
        displayed_date=start[:10] if start else "",
        coins=coins,
        categories=cats,
        impact=None,
        popularity=popularity,
        source="coindar",
        url=str(raw.get("source") or ""),
        is_estimated=False,
    )
