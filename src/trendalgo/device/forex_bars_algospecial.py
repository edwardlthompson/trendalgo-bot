"""AlgoSpecial path for Forex daily/hourly bars (budget + pace gated)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from trendalgo.brokers.forex_universe import normalize_fx_pair
from trendalgo.market.algospecial_budget import (
    PaceGate,
    can_fetch,
    min_live_refresh_minutes,
    record_fetch,
)
from trendalgo.market.algospecial_forex import derive_daily_from_h1, fetch_algospecial_h1
from trendalgo.market.ohlcv_disk_cache import load_cached_ohlcv, save_cached_ohlcv
from trendalgo.market.types import OhlcvPoint


def fetch_algospecial_daily(
    root: Path,
    symbols: list[str],
    since: datetime,
    until: datetime,
    *,
    progress: Any | None,
) -> dict[str, list[OhlcvPoint]]:
    out: dict[str, list[OhlcvPoint]] = {}
    missing: list[str] = []
    for raw in symbols:
        pair = normalize_fx_pair(raw)
        cached = load_cached_ohlcv(root, pair, "1d", since, until)
        if cached:
            out[pair] = cached
            continue
        h1 = load_cached_ohlcv(root, pair, "1h", since, until)
        if h1 and len(h1) >= 24:
            daily = derive_daily_from_h1(h1)
            if daily:
                save_cached_ohlcv(root, pair, "1d", since, until, daily)
                out[pair] = daily
                continue
        missing.append(pair)

    if not missing:
        if progress is not None:
            progress.step(len(symbols), total=len(symbols), pair="—")
        return out

    ok, reason = can_fetch(root, len(missing), n_pairs=len(symbols))
    if not ok:
        if progress is not None:
            progress.log(
                f"AlgoSpecial live skip ({reason}); using cache only",
                level="warn",
            )
            progress.step(len(symbols), total=len(symbols), pair="—")
        return out

    pace = PaceGate()
    fetched = 0
    for i, pair in enumerate(missing, start=1):
        if progress is not None:
            progress.step(len(out) + i, total=len(symbols), pair=pair)
        pace.wait()
        try:
            h1 = fetch_algospecial_h1(pair, since, until)
        except Exception as exc:  # noqa: BLE001
            if progress is not None:
                progress.log(f"{pair}: AlgoSpecial failed ({exc})", level="warn")
            continue
        fetched += 1
        if not h1:
            continue
        save_cached_ohlcv(root, pair, "1h", since, until, h1)
        daily = derive_daily_from_h1(h1)
        if daily:
            save_cached_ohlcv(root, pair, "1d", since, until, daily)
            out[pair] = daily
    if fetched:
        record_fetch(root, fetched, mark_live=True)
        if progress is not None:
            floor = min_live_refresh_minutes(len(symbols))
            progress.log(f"AlgoSpecial used {fetched} calls · next live ≥{floor}m")
    if progress is not None:
        progress.step(len(symbols), total=len(symbols), pair="—")
    return out


def fill_algospecial_hourly(
    root: Path,
    pairs: list[str],
    since: datetime,
    until: datetime,
    *,
    out: dict[str, list[OhlcvPoint]],
    progress: Any | None,
) -> None:
    missing: list[str] = []
    for raw in pairs:
        pair = normalize_fx_pair(raw)
        cached = load_cached_ohlcv(root, pair, "1h", since, until)
        if cached and len(cached) >= 24:
            out[pair] = cached
        else:
            missing.append(pair)
    if not missing:
        return
    ok, reason = can_fetch(root, len(missing), n_pairs=max(len(pairs), 59))
    if not ok:
        if progress is not None:
            progress.log(f"AlgoSpecial 1h skip ({reason})", level="warn")
        return
    pace = PaceGate()
    fetched = 0
    for i, pair in enumerate(missing, start=1):
        if progress is not None:
            progress.step(i, total=len(pairs), pair=pair)
        pace.wait()
        try:
            h1 = fetch_algospecial_h1(pair, since, until)
        except Exception as exc:  # noqa: BLE001
            if progress is not None:
                progress.log(f"{pair}: AlgoSpecial 1h failed ({exc})", level="warn")
            continue
        fetched += 1
        if h1:
            save_cached_ohlcv(root, pair, "1h", since, until, h1)
            out[pair] = h1
            daily = derive_daily_from_h1(h1)
            if daily:
                save_cached_ohlcv(root, pair, "1d", since, until, daily)
    if fetched:
        record_fetch(root, fetched, mark_live=True)
