"""CoinMarketCal official API client (x-api-key)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from typing import Any

from trendalgo.device.calendar.model import CalendarEvent
from trendalgo.device.calendar.quota import CMC_MIN_INTERVAL_S, UsageSnapshot, usage_from_dict

BASE = "https://api.coinmarketcal.com"

_last_call_monotonic: float = 0.0


class ProviderError(RuntimeError):
    pass


def test_key(api_key: str, *, timeout: float = 15.0) -> None:
    fetch_events(api_key, limit=1, timeout=timeout)


def fetch_usage(api_key: str, *, timeout: float = 15.0) -> UsageSnapshot:
    payload = _get_json(api_key, "/v2/usage", {}, timeout=timeout)
    if not isinstance(payload, dict):
        raise ProviderError("CoinMarketCal usage: unexpected payload")
    return usage_from_dict(payload)


def fetch_events(
    api_key: str,
    *,
    limit: int = 50,
    timeout: float = 20.0,
    coins: str | list[str] | None = None,
    date_from: date | str | None = None,
    date_to: date | str | None = None,
) -> list[CalendarEvent]:
    params: dict[str, str] = {"limit": str(max(1, min(limit, 100)))}
    coin_q = _coins_query(coins)
    if coin_q:
        params["coins"] = coin_q
    if date_from is not None:
        params["from"] = _iso_day(date_from)
    if date_to is not None:
        params["to"] = _iso_day(date_to)
    payload = _get_json(api_key, "/v2/events", params, timeout=timeout)
    return [_normalize(item) for item in _items(payload)]


def _get_json(
    api_key: str,
    path: str,
    params: dict[str, str],
    *,
    timeout: float,
) -> Any:
    global _last_call_monotonic
    elapsed = time.monotonic() - _last_call_monotonic
    if elapsed < CMC_MIN_INTERVAL_S:
        time.sleep(CMC_MIN_INTERVAL_S - elapsed)
    query = urllib.parse.urlencode(params)
    url = f"{BASE}{path}" + (f"?{query}" if query else "")
    req = urllib.request.Request(url, headers={"x-api-key": api_key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            _last_call_monotonic = time.monotonic()
            retry_after = resp.headers.get("Retry-After")
            if resp.status == 429:
                raise ProviderError(f"CoinMarketCal HTTP 429 retry_after={retry_after or ''}")
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        _last_call_monotonic = time.monotonic()
        retry_after = exc.headers.get("Retry-After") if exc.headers else None
        if exc.code == 429:
            raise ProviderError(f"CoinMarketCal HTTP 429 retry_after={retry_after or ''}") from exc
        raise ProviderError(f"CoinMarketCal HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"CoinMarketCal unreachable: {exc.reason}") from exc


def _coins_query(coins: str | list[str] | None) -> str:
    if coins is None:
        return ""
    if isinstance(coins, str):
        return coins.strip()
    parts = [str(c).strip() for c in coins if str(c).strip()]
    return ",".join(parts)


def _iso_day(raw: date | str) -> str:
    if isinstance(raw, date):
        return raw.isoformat()
    return str(raw)[:10]


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
                # Prefer slug for matching; keep symbol too via join path in coin_window.
                slug = str(c.get("slug") or "").strip()
                sym = str(c.get("symbol") or c.get("fullname") or "").strip()
                if slug:
                    coins.append(slug)
                if sym and sym.lower() != slug.lower():
                    coins.append(sym)
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
    date_s = str(raw.get("date") or raw.get("date_event") or "")
    return CalendarEvent(
        id=f"cmc:{raw.get('id') or date_s}:{raw.get('title') or ''}",
        title=str(raw.get("title") or raw.get("name") or "Event"),
        date=date_s,
        displayed_date=str(raw.get("displayedDate") or raw.get("displayed_date") or date_s[:10]),
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
