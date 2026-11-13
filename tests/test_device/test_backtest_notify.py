"""Unit tests for Backtest elapsed / source badge / notify copy."""

from __future__ import annotations

from trendalgo.device.backtest_notify import (
    done_status_line,
    format_cache_age,
    format_data_source,
    format_elapsed_s,
    notify_body,
    notify_title,
)
from trendalgo.device.views.backtest_done_notify import unpack_job_meta


def test_format_elapsed_s() -> None:
    assert format_elapsed_s(12) == "12s"
    assert format_elapsed_s(125) == "2m 05s"
    assert format_elapsed_s(3725) == "1h 02m"
    assert format_elapsed_s(None) == "—"


def test_format_cache_age() -> None:
    assert format_cache_age(45) == "45s ago"
    assert format_cache_age(120) == "2m ago"
    assert format_cache_age(7200) == "2h ago"


def test_format_data_source() -> None:
    assert format_data_source("kraken_ohlcv") == "Kraken public"
    assert format_data_source("synthetic") == "synthetic"
    assert "cached" in format_data_source("cache", cache_age_s=7200).lower()
    assert "2h ago" in format_data_source("cache", cache_age_s=7200)


def test_done_status_and_notify() -> None:
    line = done_status_line(elapsed_s=65, data_source="kraken_public")
    assert "1m 05s" in line or "Elapsed" in line
    assert "Source:" in line
    assert notify_title()
    assert "1m 05s" in notify_body(elapsed_s=65) or "Finished" in notify_body(elapsed_s=65)


def test_unpack_job_meta() -> None:
    meta = unpack_job_meta(
        {"rows": [], "elapsed_s": 12.5, "data_source": "cache", "cache_age_s": 90}
    )
    assert meta["elapsed_s"] == 12.5
    assert meta["data_source"] == "cache"
    assert meta["cache_age_s"] == 90.0
    assert unpack_job_meta([]) == {}
