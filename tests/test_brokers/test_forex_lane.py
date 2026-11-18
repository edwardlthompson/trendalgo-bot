"""FX-P1…P4: forex universe, sessions, research BT, macro fixture."""

from __future__ import annotations

from datetime import date

from trendalgo.brokers.forex_research import forex_buy_hold_bt
from trendalgo.brokers.forex_universe import (
    clear_forex_universe_cache,
    is_forex_pair,
    load_forex_universe,
    normalize_fx_pair,
)
from trendalgo.device.calendar.providers.macro_calendar import rows_to_events
from trendalgo.device.support_matrix import clear_support_matrix_cache, venue_by_id
from trendalgo.market.fx_sessions import is_fx_weekend, validate_fx_daily_bars


def test_forex_universe_size() -> None:
    clear_forex_universe_cache()
    pairs = load_forex_universe()
    assert 40 <= len(pairs) <= 80
    assert is_forex_pair("eurusd")
    assert normalize_fx_pair("eurusd") == "EUR/USD"


def test_fx_weekend_gap_ok() -> None:
    summary = validate_fx_daily_bars(
        [date(2026, 3, 13), date(2026, 3, 16)],
        since=date(2026, 3, 13),
        until=date(2026, 3, 16),
    )
    assert summary.unexpected_gaps == 0
    assert is_fx_weekend(date(2026, 3, 14))


def test_forex_buy_hold_synthetic() -> None:
    result = forex_buy_hold_bt("EUR/USD")
    assert result.bar_count >= 1
    assert result.source == "synthetic"
    assert "Alpaca" in result.disclaimer or "synthetic" in result.disclaimer.lower()


def test_macro_rows_to_events() -> None:
    events = rows_to_events([{"name": "CPI", "time": "2026-03-12T12:30:00Z", "currency": "USD"}])
    assert len(events) == 1
    assert events[0].source == "macro"
    assert events[0].coins == ("USD",)


def test_matrix_forex_partial() -> None:
    clear_support_matrix_cache()
    fx = venue_by_id("forex")
    assert fx is not None
    assert fx.live_trade == "no"
    assert fx.status == "partial"
