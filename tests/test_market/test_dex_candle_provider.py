"""DEX-P2b: labeled DEX candle provider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from trendalgo.device.support_matrix import clear_support_matrix_cache, venue_by_id
from trendalgo.market.dex_candle_catalog import list_dex_candle_pairs
from trendalgo.market.dex_candle_provider import fetch_dex_candles
from trendalgo.market.dex_cex_proxy import cex_proxy_disclaimer, resolve_cex_proxy
from trendalgo.market.types import OhlcvPoint


def test_catalog_ethereum_base() -> None:
    eth = list_dex_candle_pairs("ethereum")
    base = list_dex_candle_pairs("base")
    assert eth and base
    assert list_dex_candle_pairs("arbitrum") == ()


def test_cex_proxy_maps_usdc_to_usd() -> None:
    cex, pair = resolve_cex_proxy("base", "ETH/USDC")
    assert cex == "coinbaseadvanced"
    assert pair == "ETH/USD"
    assert "CEX spot proxy" in cex_proxy_disclaimer("base", cex)


def test_synthetic_prefer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_MARKET_SOURCE", "synthetic")
    until = datetime.now(UTC)
    since = until - timedelta(days=3)
    result = fetch_dex_candles("ethereum", "ETH/USDC", "1h", since, until)
    assert result.meta.kind == "synthetic"
    assert result.meta.degraded
    assert len(result.points) >= 1


def test_aggregator_injectable() -> None:
    until = datetime.now(UTC)
    since = until - timedelta(hours=2)

    def fake_agg(ref, timeframe, s, u):  # noqa: ANN001
        _ = (ref, timeframe, s, u)
        return [OhlcvPoint(time=1, open=1, high=1, low=1, close=1, volume=1)]

    result = fetch_dex_candles(
        "base",
        "ETH/USDC",
        "1h",
        since,
        until,
        prefer="aggregator",
        aggregator=fake_agg,
    )
    assert result.meta.kind == "aggregator"
    assert result.meta.provider_id == "geckoterminal"
    assert not result.meta.degraded


def test_auto_falls_back_when_aggregator_fails() -> None:
    until = datetime.now(UTC)
    since = until - timedelta(days=1)

    def boom(*_a, **_k):  # noqa: ANN001
        raise RuntimeError("no network")

    result = fetch_dex_candles(
        "base",
        "ETH/USDC",
        "1h",
        since,
        until,
        prefer="auto",
        aggregator=boom,
    )
    assert result.meta.kind == "synthetic"
    assert result.meta.degraded


def test_matrix_deep_ohlcv_partial() -> None:
    clear_support_matrix_cache()
    assert venue_by_id("ethereum").deep_ohlcv_bt == "partial"  # type: ignore[union-attr]
    assert venue_by_id("base").deep_ohlcv_bt == "partial"  # type: ignore[union-attr]


def test_readme_table_still_matches(tmp_path: Path) -> None:
    _ = tmp_path
    from trendalgo.device.support_matrix_readme import (
        extract_marked_block,
        render_exchange_support_table,
    )

    root = Path(__file__).resolve().parents[2]
    text = (root / "README.md").read_text(encoding="utf-8")
    inner = extract_marked_block(text)
    assert inner is not None
    assert inner.strip() == render_exchange_support_table().strip()
