"""CoinMarketCal query encoding + refresh budget gates."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from trendalgo.device.calendar import refresh as refresh_mod
from trendalgo.device.calendar.cache import save_events
from trendalgo.device.calendar.model import CalendarEvent
from trendalgo.device.calendar.providers import coinmarketcal
from trendalgo.device.calendar.quota import UsageSnapshot


def test_fetch_events_encodes_coins_and_dates(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get(api_key: str, path: str, params: dict[str, str], *, timeout: float) -> Any:
        captured["path"] = path
        captured["params"] = dict(params)
        return {
            "data": [
                {
                    "id": "1",
                    "title": "Test",
                    "date": "2026-11-16T00:00:00Z",
                    "displayedDate": "16 Nov 2026",
                    "coins": [{"slug": "bitcoin", "symbol": "btc", "name": "Bitcoin"}],
                }
            ]
        }

    monkeypatch.setattr(coinmarketcal, "_get_json", fake_get)
    rows = coinmarketcal.fetch_events(
        "key",
        coins=["bitcoin", "ethereum"],
        date_from=date(2026, 11, 15),
        date_to=date(2026, 11, 22),
        limit=100,
    )
    assert captured["path"] == "/v2/events"
    assert captured["params"]["coins"] == "bitcoin,ethereum"
    assert captured["params"]["from"] == "2026-11-15"
    assert captured["params"]["to"] == "2026-11-22"
    assert rows[0].coins[0] == "bitcoin"


def test_refresh_skips_when_cache_fresh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import UTC, datetime

    save_events(
        tmp_path,
        [
            CalendarEvent(
                id="1",
                title="Cached",
                date=datetime.now(tz=UTC).isoformat(),
                displayed_date="today",
                coins=("BTC",),
            )
        ],
        fetched_at=datetime.now(tz=UTC).isoformat(),
    )
    monkeypatch.setattr(refresh_mod.vault, "read_cmc_key", lambda _s=None: "k")
    monkeypatch.setattr(refresh_mod.vault, "read_coindar_token", lambda _s=None: None)

    def boom(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("must not call network when cache fresh")

    monkeypatch.setattr(coinmarketcal, "fetch_usage", boom)
    monkeypatch.setattr(coinmarketcal, "fetch_events", boom)
    out = refresh_mod.refresh_cache(tmp_path)
    assert out[0].title == "Cached"


def test_refresh_skips_on_quota_reserve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import UTC, datetime, timedelta

    save_events(
        tmp_path,
        [
            CalendarEvent(
                id="1",
                title="Old",
                date=datetime.now(tz=UTC).isoformat(),
                displayed_date="today",
                coins=("BTC",),
            )
        ],
        fetched_at=(datetime.now(tz=UTC) - timedelta(hours=12)).isoformat(),
    )
    monkeypatch.setattr(refresh_mod.vault, "read_cmc_key", lambda _s=None: "k")
    monkeypatch.setattr(refresh_mod.vault, "read_coindar_token", lambda _s=None: None)
    monkeypatch.setattr(
        coinmarketcal,
        "fetch_usage",
        lambda *_a, **_k: UsageSnapshot(
            tier="free",
            period_ym="2026-11",
            request_count=2960,
            monthly_quota=3000,
            remaining=40,
            quota_reset_at="2026-12-01T00:00:00Z",
        ),
    )
    monkeypatch.setattr(
        coinmarketcal,
        "fetch_events",
        MagicMock(side_effect=AssertionError("no events fetch")),
    )
    out = refresh_mod.refresh_cache(tmp_path)
    assert out[0].title == "Old"
