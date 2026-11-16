"""Cache-only coin event window (no network). Free ahead clamp = 7d."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from trendalgo.device.calendar import cache
from trendalgo.device.calendar.model import CalendarEvent, sort_events
from trendalgo.device.calendar.quota import CMC_FREE_AHEAD_DAYS, effective_ahead_days


def coin_keys(coin: dict[str, Any] | str) -> set[str]:
    """Uppercased match keys: symbol, pair base, cmc_slug."""
    if isinstance(coin, str):
        raw = coin.strip()
        if "/" in raw:
            raw = raw.split("/", 1)[0]
        return {raw.upper()} if raw else set()
    keys: set[str] = set()
    for field in ("symbol", "cmc_slug", "gecko_id"):
        val = coin.get(field)
        if val:
            keys.add(str(val).strip().upper())
    pair = str(coin.get("pair") or "")
    if pair:
        keys.add(pair.split("/", 1)[0].strip().upper())
    identity = coin.get("identity")
    if isinstance(identity, dict):
        for field in ("cmc_slug", "symbol"):
            val = identity.get(field)
            if val:
                keys.add(str(val).strip().upper())
    return {k for k in keys if k}


def events_in_window(
    events: list[CalendarEvent],
    *,
    keys: set[str],
    past_days: int = 30,
    ahead_days: int = CMC_FREE_AHEAD_DAYS,
    now: date | None = None,
) -> list[CalendarEvent]:
    """Events whose coins intersect ``keys`` and date in [now-past, now+ahead]."""
    if not keys:
        return []
    want = {k.upper() for k in keys}
    today = now or datetime.now(tz=UTC).date()
    start = today - timedelta(days=max(0, past_days))
    end = today + timedelta(days=max(0, ahead_days))
    out: list[CalendarEvent] = []
    for event in events:
        day = _parse_day(event.date)
        if day is None or day < start or day > end:
            continue
        coins = {c.upper() for c in event.coins}
        if coins and coins.isdisjoint(want):
            continue
        if not coins:
            continue
        out.append(event)
    return sort_events(out, "date")


def has_coin_events(
    root: Path,
    coin: dict[str, Any] | str,
    *,
    tier: str | None = "free",
    past_days: int = 30,
) -> bool:
    return bool(load_coin_events(root, coin, tier=tier, past_days=past_days))


def load_coin_events(
    root: Path,
    coin: dict[str, Any] | str,
    *,
    tier: str | None = "free",
    past_days: int = 30,
) -> list[CalendarEvent]:
    """Filter cached events for one coin. Cache only — never hits the network."""
    ahead = effective_ahead_days(tier)
    return events_in_window(
        cache.load_events(root),
        keys=coin_keys(coin),
        past_days=past_days,
        ahead_days=ahead,
    )


def parse_event_day(raw: str) -> date | None:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def _parse_day(raw: str) -> date | None:
    return parse_event_day(raw)
