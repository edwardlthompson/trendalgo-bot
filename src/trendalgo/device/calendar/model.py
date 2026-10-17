"""Normalized calendar event + filter helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    title: str
    date: str
    displayed_date: str
    coins: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    impact: float | None = None
    popularity: int | None = None
    source: str = "coinmarketcal"
    url: str = ""
    is_estimated: bool = False


@dataclass
class CalendarFilters:
    holdings_only: bool = True
    horizon_days: int = 30
    impact_min: float | None = 5.0
    sources: tuple[str, ...] = ("coinmarketcal", "coindar")
    categories: tuple[str, ...] = ()
    sort: str = "date"  # date | impact | popularity
    confirmed_only: bool = False


def dedupe_key(event: CalendarEvent) -> str:
    coin = event.coins[0].lower() if event.coins else ""
    return f"{event.title.strip().lower()}|{event.date[:10]}|{coin}"


def merge_events(batches: list[list[CalendarEvent]]) -> list[CalendarEvent]:
    by_key: dict[str, CalendarEvent] = {}
    for batch in batches:
        for event in batch:
            key = dedupe_key(event)
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = event
                continue
            # Prefer CoinMarketCal impact when both match.
            if existing.impact is None and event.impact is not None:
                by_key[key] = event
            elif existing.source != "coinmarketcal" and event.source == "coinmarketcal":
                by_key[key] = event
    return list(by_key.values())


def apply_filters(
    events: list[CalendarEvent],
    filters: CalendarFilters,
    *,
    holding_symbols: set[str],
) -> list[CalendarEvent]:
    now = datetime.now(tz=UTC).date()
    end = now + timedelta(days=max(1, filters.horizon_days))
    out: list[CalendarEvent] = []
    for event in events:
        if event.source not in filters.sources:
            continue
        if filters.confirmed_only and event.is_estimated:
            continue
        day = _parse_day(event.date)
        if day is None or day < now or day > end:
            continue
        if filters.holdings_only and holding_symbols:
            coins = {c.upper() for c in event.coins}
            if coins and coins.isdisjoint(holding_symbols):
                continue
        if filters.impact_min is not None and event.impact is not None:
            if event.impact < filters.impact_min:
                continue
        if filters.categories:
            cats = {c.lower() for c in event.categories}
            want = {c.lower() for c in filters.categories}
            if cats and cats.isdisjoint(want):
                continue
        out.append(event)
    return sort_events(out, filters.sort)


def sort_events(events: list[CalendarEvent], sort: str) -> list[CalendarEvent]:
    if sort == "impact":
        return sorted(events, key=lambda e: (e.impact is None, -(e.impact or 0), e.date))
    if sort == "popularity":
        return sorted(events, key=lambda e: (e.popularity is None, -(e.popularity or 0), e.date))
    return sorted(events, key=lambda e: e.date)


def event_to_dict(event: CalendarEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "title": event.title,
        "date": event.date,
        "displayed_date": event.displayed_date,
        "coins": list(event.coins),
        "categories": list(event.categories),
        "impact": event.impact,
        "popularity": event.popularity,
        "source": event.source,
        "url": event.url,
        "is_estimated": event.is_estimated,
    }


def event_from_dict(raw: dict[str, Any]) -> CalendarEvent:
    return CalendarEvent(
        id=str(raw.get("id") or ""),
        title=str(raw.get("title") or ""),
        date=str(raw.get("date") or ""),
        displayed_date=str(raw.get("displayed_date") or raw.get("date") or ""),
        coins=tuple(str(c) for c in (raw.get("coins") or ())),
        categories=tuple(str(c) for c in (raw.get("categories") or ())),
        impact=_float_or_none(raw.get("impact")),
        popularity=_int_or_none(raw.get("popularity")),
        source=str(raw.get("source") or "coinmarketcal"),
        url=str(raw.get("url") or ""),
        is_estimated=bool(raw.get("is_estimated")),
    )


def _parse_day(raw: str) -> Any:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def _float_or_none(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _int_or_none(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None
