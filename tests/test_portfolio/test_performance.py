"""Portfolio performance history tests."""

from datetime import UTC, datetime
from pathlib import Path

from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.performance import (
    PERFORMANCE_RANGES,
    btc_usd_price_at,
    build_performance_payload,
    ensure_btc_dry_run_fixture,
    performance_curve,
)


def test_btc_fixture_seeds_one_year(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    account_id = store.get_or_create_account("kraken", "default")
    seeded = ensure_btc_dry_run_fixture(store, account_id)
    assert seeded is True
    assert store.count_daily_aggregates(account_id) == 366
    snap = store.latest_snapshot(account_id)
    assert snap is not None
    assert len(snap["holdings"]) == 1
    assert snap["holdings"][0]["asset"] == "BTC"
    assert float(snap["holdings"][0]["quantity"]) == 1.0
    assert ensure_btc_dry_run_fixture(store, account_id) is False


def test_performance_curve_ranges(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    account_id = store.get_or_create_account("kraken", "default")
    ensure_btc_dry_run_fixture(store, account_id)
    anchor = datetime(2026, 6, 26, 12, 0, 0, tzinfo=UTC)
    for key in PERFORMANCE_RANGES:
        payload = build_performance_payload(store, account_id, key, dry_run=False)
        points = payload["points"]
        assert len(points) >= 2  # type: ignore[arg-type]
        assert len(payload["top10_index"]) == len(points)  # type: ignore[arg-type]
        if key in ("1y", "6m", "3m", "1m"):
            assert payload["granularity"] == "1d"  # type: ignore[operator]
        else:
            assert payload["granularity"] == "1h"  # type: ignore[operator]
    hourly = performance_curve(store, account_id, "24h", now=anchor)
    assert len(hourly) >= 20
    assert len(performance_curve(store, account_id, "7d", now=anchor)) >= 168
    assert len(performance_curve(store, account_id, "14d", now=anchor)) >= 336
    assert len(performance_curve(store, account_id, "1y", now=anchor)) >= 360


def test_build_performance_payload_includes_comparison(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    account_id = store.get_or_create_account("kraken", "default")
    ensure_btc_dry_run_fixture(store, account_id)
    payload = build_performance_payload(store, account_id, "1y", dry_run=False)
    assert "comparison" in payload
    assert "alpha_pct" in payload["comparison"]  # type: ignore[operator]


def test_btc_price_is_deterministic() -> None:
    ts = datetime(2025, 6, 26, tzinfo=UTC)
    assert btc_usd_price_at(ts) == btc_usd_price_at(ts)
