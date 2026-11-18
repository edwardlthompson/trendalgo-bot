"""Fetch + merge calendar events into the local cache (quota-aware)."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from trendalgo.brokers.tradfi_universe import load_tradfi_universe
from trendalgo.device.calendar import cache, vault
from trendalgo.device.calendar.model import CalendarEvent, merge_events
from trendalgo.device.calendar.nasdaq_quota import (
    NASDAQ_MAX_REQ_PER_DAY,
    budget_from_dict,
    trading_days_ahead,
)
from trendalgo.device.calendar.nasdaq_quota import (
    can_refresh as nasdaq_can_refresh,
)
from trendalgo.device.calendar.providers import (
    coindar,
    coinmarketcal,
    macro_calendar,
    nasdaq_calendar,
)
from trendalgo.device.calendar.providers.coinmarketcal import ProviderError
from trendalgo.device.calendar.quota import (
    CMC_FREE_AHEAD_DAYS,
    cache_age_seconds,
    can_spend_refresh,
    effective_ahead_days,
)
from trendalgo.device.wizard.credentials import CredentialStore
from trendalgo.market.us_equity_sessions import is_rth_session_day

_NASDAQ_BUDGET_FILE = "nasdaq_calendar_budget.json"


def _nasdaq_budget_path(root: Path) -> Path:
    return root / _NASDAQ_BUDGET_FILE


def _load_nasdaq_budget(root: Path) -> dict:
    path = _nasdaq_budget_path(root)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_nasdaq_budget(root: Path, day: str, count: int) -> None:
    path = _nasdaq_budget_path(root)
    path.write_text(json.dumps({"day": day, "request_count": count}), encoding="utf-8")


def refresh_cache(
    root: Path,
    store: CredentialStore | None = None,
    *,
    coins: list[str] | None = None,
    force: bool = False,
) -> list[CalendarEvent]:
    """Refresh local cache. CMC Free budget + throttled NASDAQ/macro by lane."""
    age = cache_age_seconds(cache.fetched_at(root))
    if not force:
        ok, _reason = can_spend_refresh(None, cache_age_s=age)
        if not ok:
            return cache.load_events(root)

    # Desks are always visible; Auto-scan prefs do not gate calendars.
    cmc = vault.read_cmc_key(store)
    tier = "free"
    if cmc and not force:
        try:
            usage = coinmarketcal.fetch_usage(cmc)
            tier = usage.tier
            ok, _reason = can_spend_refresh(usage, cache_age_s=None)
            if not ok:
                return cache.load_events(root)
        except ProviderError:
            pass

    batches: list[list[CalendarEvent]] = []
    ahead = effective_ahead_days(tier)
    today = datetime.now(tz=UTC).date()
    date_from: date = today
    date_to: date = today + timedelta(days=max(CMC_FREE_AHEAD_DAYS, ahead))

    if cmc:
        try:
            batches.append(
                coinmarketcal.fetch_events(
                    cmc,
                    limit=100,
                    coins=coins,
                    date_from=date_from,
                    date_to=date_to,
                )
            )
        except ProviderError:
            pass
    token = vault.read_coindar_token(store)
    if token:
        try:
            batches.append(coindar.fetch_events(token))
        except ProviderError:
            pass

    batches.append(_refresh_nasdaq(root, age=age, force=force))
    batches.append(macro_calendar.fetch_macro_events())

    events = merge_events(batches)
    if events:
        cache.save_events(root, events, fetched_at=datetime.now(tz=UTC).isoformat())
        return events
    return cache.load_events(root)


def _refresh_nasdaq(
    root: Path,
    *,
    age: float | None,
    force: bool,
) -> list[CalendarEvent]:
    budget = budget_from_dict(_load_nasdaq_budget(root))
    if not force:
        ok, _reason = nasdaq_can_refresh(cache_age_s=age, budget=budget)
        if not ok:
            return []
    universe = set(load_tradfi_universe(root=root))
    today = datetime.now(tz=UTC).date()
    days = [d for d in trading_days_ahead(today) if is_rth_session_day(d)]
    out: list[CalendarEvent] = []
    used = budget.request_count
    for day in days:
        if used >= NASDAQ_MAX_REQ_PER_DAY:
            break
        batch = nasdaq_calendar.fetch_earnings_day(day, sleep_s=1.0 if used else 0.0)
        used += 1
        out.extend(nasdaq_calendar.filter_universe(batch, universe))
    _save_nasdaq_budget(root, budget.day, used)
    return out
