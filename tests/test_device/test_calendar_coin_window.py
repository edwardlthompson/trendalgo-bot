"""Coin calendar window filter + Free ahead clamp (cache only)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from trendalgo.device.calendar.cache import save_events
from trendalgo.device.calendar.coin_window import (
    coin_keys,
    events_in_window,
    has_coin_events,
    load_coin_events,
)
from trendalgo.device.calendar.model import CalendarEvent
from trendalgo.device.calendar.quota import (
    CMC_FREE_AHEAD_DAYS,
    UsageSnapshot,
    can_spend_refresh,
    effective_ahead_days,
)
from trendalgo.device.calendar.timeline_layout import pack_callouts


def _ev(
    *,
    title: str,
    day: date,
    coins: tuple[str, ...] = ("BTC",),
    estimated: bool = False,
) -> CalendarEvent:
    iso = day.isoformat() + "T12:00:00Z"
    return CalendarEvent(
        id=f"t:{title}:{iso}",
        title=title,
        date=iso,
        displayed_date=day.isoformat(),
        coins=coins,
        is_estimated=estimated,
    )


def test_coin_keys_from_pair_and_slug() -> None:
    keys = coin_keys({"symbol": "eth", "pair": "ETH/USD", "cmc_slug": "ethereum"})
    assert "ETH" in keys
    assert "ETHEREUM" in keys


def test_events_in_window_respects_ahead_and_keys() -> None:
    today = date(2026, 11, 15)
    events = [
        _ev(title="past", day=today - timedelta(days=10)),
        _ev(title="soon", day=today + timedelta(days=3)),
        _ev(title="far", day=today + timedelta(days=20)),
        _ev(title="other", day=today + timedelta(days=2), coins=("SOL",)),
    ]
    kept = events_in_window(
        events,
        keys={"BTC"},
        past_days=30,
        ahead_days=CMC_FREE_AHEAD_DAYS,
        now=today,
    )
    titles = [e.title for e in kept]
    assert titles == ["past", "soon"]


def test_effective_ahead_days_free_vs_paid() -> None:
    assert effective_ahead_days("free") == 7
    assert effective_ahead_days("standard") == 30


def test_has_coin_events_cache_only(tmp_path: Path) -> None:
    today = datetime.now(tz=UTC).date()
    save_events(
        tmp_path,
        [_ev(title="near", day=today + timedelta(days=2), coins=("BTC", "bitcoin"))],
        fetched_at=datetime.now(tz=UTC).isoformat(),
    )
    assert has_coin_events(tmp_path, {"symbol": "BTC", "pair": "BTC/USD"})
    assert not has_coin_events(tmp_path, {"symbol": "DOGE", "pair": "DOGE/USD"})
    assert load_coin_events(tmp_path, "BTC/USD")[0].title == "near"


def test_can_spend_refresh_reserve_and_fresh() -> None:
    usage = UsageSnapshot(
        tier="free",
        period_ym="2026-11",
        request_count=2960,
        monthly_quota=3000,
        remaining=40,
        quota_reset_at="2026-12-01T00:00:00Z",
    )
    ok, reason = can_spend_refresh(usage, cache_age_s=30_000)
    assert ok is False
    assert reason == "quota_reserve"
    ok2, reason2 = can_spend_refresh(
        UsageSnapshot(
            tier="free",
            period_ym="2026-11",
            request_count=10,
            monthly_quota=3000,
            remaining=2990,
            quota_reset_at="2026-12-01T00:00:00Z",
        ),
        cache_age_s=60,
    )
    assert ok2 is False
    assert reason2 == "cache_fresh"


def test_pack_callouts_suppresses_close_neighbors() -> None:
    today = date(2026, 11, 15)
    packed = pack_callouts(
        [
            (today, "A", today.isoformat(), False, ""),
            (today + timedelta(days=1), "B", "b", False, ""),
            (today + timedelta(days=5), "C", "c", False, ""),
        ],
        min_gap_days=3.0,
    )
    assert [m.show_callout for m in packed] == [True, False, True]
    assert packed[0].index == 1
