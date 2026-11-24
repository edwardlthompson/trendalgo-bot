"""AV-G-RES4 — coin events timeline payload (hint, closes, marker_frac)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from trendalgo.device.calendar.cache import save_events
from trendalgo.device.calendar.model import CalendarEvent
from trendalgo.results_store.desk_events import events_timeline_payload


def test_events_timeline_payload_empty(tmp_path: Path) -> None:
    coin = {"pair": "BTC/USD", "symbol": "BTC", "spark_closes_30d": [1.0, 1.1, 1.2]}
    payload = events_timeline_payload(tmp_path, coin, "BTC/USD")
    assert payload["pair"] == "BTC/USD"
    assert payload["symbol"] == "BTC"
    assert payload["count"] == 0
    assert payload["closes"] == [1.0, 1.1, 1.2]
    assert "Events" in payload["title"]
    assert payload["hint"]
    assert payload["empty"]


def test_events_timeline_payload_markers(tmp_path: Path) -> None:
    today = datetime.now(tz=UTC).date()
    day = today - timedelta(days=5)
    iso = day.isoformat() + "T12:00:00Z"
    save_events(
        tmp_path,
        [
            CalendarEvent(
                id="t:upgrade",
                title="Upgrade",
                date=iso,
                displayed_date=day.isoformat(),
                coins=("BTC",),
                categories=("Release",),
                source="cmc",
                url="https://example.test/btc",
                is_estimated=False,
            )
        ],
        fetched_at=datetime.now(tz=UTC).isoformat(),
    )
    coin = {
        "pair": "BTC/USD",
        "symbol": "BTC",
        "spark_closes_30d": [10.0, 11.0, 12.0, 11.5],
    }
    payload = events_timeline_payload(tmp_path, coin, "BTC/USD")
    assert payload["count"] >= 1
    row = payload["rows"][0]
    assert row["title"] == "Upgrade"
    assert 0.0 <= float(row["marker_frac"]) <= 1.0
    assert row["source"] in {"cmc", "Release"}
    assert len(payload["closes"]) == 4
