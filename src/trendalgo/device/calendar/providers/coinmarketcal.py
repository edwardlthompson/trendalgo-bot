"""CoinMarketCal official API client (x-api-key)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from trendalgo.device.calendar.model import CalendarEvent

BASE = "https://api.coinmarketcal.com"


class ProviderError(RuntimeError):
    pass


def test_key(api_key: str, *, timeout: float = 15.0) -> None:
    fetch_events(api_key, limit=1, timeout=timeout)


def fetch_events(
    api_key: str,
    *,
    limit: int = 50,
    timeout: float = 20.0,
) -> list[CalendarEvent]:
    query = urllib.parse.urlencode({"limit": max(1, min(limit, 100))})
    url = f"{BASE}/v2/events?{query}"
    req = urllib.request.Request(url, headers={"x-api-key": api_key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"CoinMarketCal HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"CoinMarketCal unreachable: {exc.reason}") from exc
    return [_normalize(item) for item in _items(payload)]


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, dict):
        body = payload.get("body") or payload.get("data") or payload.get("events")
        if isinstance(body, list):
            return [p for p in body if isinstance(p, dict)]
    return []


def _normalize(raw: dict[str, Any]) -> CalendarEvent:
    coins_raw = raw.get("coins") or raw.get("coin") or []
    coins: list[str] = []
    if isinstance(coins_raw, list):
        for c in coins_raw:
            if isinstance(c, dict):
                coins.append(str(c.get("symbol") or c.get("fullname") or c.get("slug") or ""))
            else:
                coins.append(str(c))
    cats_raw = raw.get("categories") or raw.get("category") or []
    cats: list[str] = []
    if isinstance(cats_raw, list):
        for c in cats_raw:
            if isinstance(c, dict):
                cats.append(str(c.get("name") or c.get("id") or ""))
            else:
                cats.append(str(c))
    elif isinstance(cats_raw, str):
        cats.append(cats_raw)
    date = str(raw.get("date") or raw.get("date_event") or "")
    return CalendarEvent(
        id=f"cmc:{raw.get('id') or date}:{raw.get('title') or ''}",
        title=str(raw.get("title") or raw.get("name") or "Event"),
        date=date,
        displayed_date=str(raw.get("displayedDate") or raw.get("displayed_date") or date[:10]),
        coins=tuple(c for c in coins if c),
        categories=tuple(c for c in cats if c),
        impact=_impact(raw),
        popularity=None,
        source="coinmarketcal",
        url=str(raw.get("source") or raw.get("proof") or raw.get("url") or ""),
        is_estimated=bool(raw.get("isEstimated") or raw.get("is_estimated")),
    )


def _impact(raw: dict[str, Any]) -> float | None:
    for key in ("impact", "impact_score", "percentage", "vote_count"):
        if key in raw and raw[key] is not None:
            try:
                val = float(raw[key])
            except (TypeError, ValueError):
                continue
            if key == "percentage":
                return round(val / 10.0, 2)
            return val
    return None
