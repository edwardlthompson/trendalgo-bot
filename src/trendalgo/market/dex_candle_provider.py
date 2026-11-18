"""Fetch labeled candles for DEX majors (DEX-P2b). Offline-safe default."""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime
from typing import Literal, cast

from trendalgo.market.dex_candle_catalog import DEX_CANDLE_VENUES, list_dex_candle_pairs
from trendalgo.market.dex_candle_types import DexCandleResult, DexCandleSourceMeta, DexPairRef
from trendalgo.market.dex_cex_proxy import cex_proxy_disclaimer, resolve_cex_proxy
from trendalgo.market.ohlcv_provider import fetch_ohlcv
from trendalgo.market.synthetic import synthetic_ohlcv
from trendalgo.market.types import OhlcvPoint

Prefer = Literal["auto", "aggregator", "cex_proxy", "synthetic"]
AggregatorFn = Callable[[DexPairRef, str, datetime, datetime], list[OhlcvPoint]]


def _ref_for(venue_id: str, pair: str, pool_address: str | None) -> DexPairRef:
    for ref in list_dex_candle_pairs(venue_id):
        if ref.pair.upper() == pair.upper() and (
            pool_address is None or ref.pool_address == pool_address.lower()
        ):
            return ref
    return DexPairRef(
        venue_id=venue_id,
        pair=pair,
        pool_address=(pool_address or "").lower(),
        fee_tier=0,
    )


def _synthetic_result(
    ref: DexPairRef, timeframe: str, since: datetime, until: datetime
) -> DexCandleResult:
    points = tuple(synthetic_ohlcv(ref.pair, timeframe, since, until))
    return DexCandleResult(
        points=points,
        meta=DexCandleSourceMeta(
            venue_id=ref.venue_id,
            pair=ref.pair,
            kind="synthetic",
            provider_id="synthetic",
            cache_source=f"{ref.venue_id}_synthetic",
            pool_address=ref.pool_address or None,
            degraded=True,
            disclaimer="Offline/synthetic candles — research only.",
        ),
    )


def _proxy_result(
    ref: DexPairRef, timeframe: str, since: datetime, until: datetime
) -> DexCandleResult:
    cex_id, cex_pair = resolve_cex_proxy(ref.venue_id, ref.pair)
    points = tuple(fetch_ohlcv(cex_id, cex_pair, timeframe, since, until))
    return DexCandleResult(
        points=points,
        meta=DexCandleSourceMeta(
            venue_id=ref.venue_id,
            pair=ref.pair,
            kind="cex_proxy",
            provider_id=cex_id,
            cache_source=f"{ref.venue_id}_cex_proxy:{cex_id}",
            pool_address=ref.pool_address or None,
            degraded=True,
            disclaimer=cex_proxy_disclaimer(ref.venue_id, cex_id),
        ),
    )


def fetch_dex_candles(
    venue_id: str,
    pair: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    pool_address: str | None = None,
    prefer: Prefer | None = None,
    aggregator: AggregatorFn | None = None,
) -> DexCandleResult:
    """Return candles with honesty metadata. Never claims on-chain fills."""
    vid = venue_id.strip().lower()
    if vid not in DEX_CANDLE_VENUES:
        raise ValueError(f"unsupported DEX candle venue: {vid}")
    raw_prefer = prefer or os.environ.get("TRENDALGO_DEX_CANDLE_PREFER", "auto")
    mode: Prefer = (
        cast(Prefer, raw_prefer)
        if raw_prefer in {"auto", "aggregator", "cex_proxy", "synthetic"}
        else "auto"
    )
    # Explicit prefer wins; env synthetic only forces default/auto path.
    if (
        prefer is None
        and os.environ.get("TRENDALGO_MARKET_SOURCE", "").strip().lower() == "synthetic"
    ):
        mode = "synthetic"
    ref = _ref_for(vid, pair, pool_address)

    if mode == "synthetic":
        return _synthetic_result(ref, timeframe, since, until)
    if mode == "cex_proxy":
        return _proxy_result(ref, timeframe, since, until)
    if mode == "aggregator":
        if aggregator is None:
            raise RuntimeError("aggregator backend not configured")
        points = tuple(aggregator(ref, timeframe, since, until))
        return DexCandleResult(
            points=points,
            meta=DexCandleSourceMeta(
                venue_id=ref.venue_id,
                pair=ref.pair,
                kind="aggregator",
                provider_id="geckoterminal",
                cache_source=f"{ref.venue_id}_geckoterminal",
                pool_address=ref.pool_address or None,
                degraded=False,
                disclaimer="On-chain pool OHLC from aggregator; not execution prices.",
            ),
        )
    # auto: aggregator if provided, else synthetic (CI-safe; no live HTTP)
    if aggregator is not None:
        try:
            return fetch_dex_candles(
                vid,
                pair,
                timeframe,
                since,
                until,
                pool_address=pool_address,
                prefer="aggregator",
                aggregator=aggregator,
            )
        except Exception:
            pass
    return _synthetic_result(ref, timeframe, since, until)
