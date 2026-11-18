"""Forex daily/hourly bars: Alpaca when granted, else AlgoSpecial H1 (+ D1 derived)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from trendalgo.brokers.forex_universe import normalize_fx_pair
from trendalgo.device.forex_bars_algospecial import (
    fetch_algospecial_daily,
    fill_algospecial_hourly,
)
from trendalgo.market.alpaca_forex import AlpacaForexRatesProvider, fetch_alpaca_forex_rates
from trendalgo.market.ohlcv_disk_cache import load_cached_ohlcv, save_cached_ohlcv
from trendalgo.market.types import OhlcvPoint

_FX_WORKERS = 8


def alpaca_fx_available(probe: str, since: datetime, until: datetime) -> bool:
    try:
        live = fetch_alpaca_forex_rates(probe, "1d", since, until)
    except Exception:  # noqa: BLE001
        return False
    return bool(live)


def fetch_forex_daily_bars(
    root: Path,
    symbols: list[str],
    since: datetime,
    until: datetime,
    *,
    progress: Any | None = None,
) -> dict[str, list[OhlcvPoint]]:
    """Return pair → daily bars. Prefer Alpaca; else AlgoSpecial H1→D1."""
    if not symbols:
        return {}
    probe = normalize_fx_pair(symbols[0])
    if alpaca_fx_available(probe, since, until):
        if progress is not None:
            progress.log("Forex bars: Alpaca rates")
        return _fetch_alpaca_daily(root, symbols, since, until, progress=progress)
    if progress is not None:
        progress.log("Forex bars: AlgoSpecial H1 (D1 derived); Alpaca FX unavailable")
    return fetch_algospecial_daily(root, symbols, since, until, progress=progress)


def fetch_forex_hourly_bars(
    root: Path,
    pairs: list[str],
    since: datetime,
    until: datetime,
    *,
    out: dict[str, list[OhlcvPoint]],
    progress: Any | None = None,
) -> None:
    """Fill ``out`` with 1h bars (Alpaca or AlgoSpecial). Mutates ``out``."""
    if not pairs:
        return
    probe = normalize_fx_pair(pairs[0])
    use_alpaca = alpaca_fx_available(probe, since, until)
    if use_alpaca:
        provider = AlpacaForexRatesProvider(allow_synthetic_fallback=False)
        for i, raw in enumerate(pairs, start=1):
            pair = normalize_fx_pair(raw)
            if progress is not None:
                progress.step(i, total=len(pairs), pair=pair)
            cached = load_cached_ohlcv(root, pair, "1h", since, until)
            if cached and len(cached) >= 24:
                out[pair] = cached
                continue
            try:
                points = provider.fetch("alpaca", pair, "1h", since, until)
            except Exception:  # noqa: BLE001
                points = []
            if points and str(getattr(provider, "last_source", "")) == "alpaca":
                save_cached_ohlcv(root, pair, "1h", since, until, points)
                out[pair] = points
            elif progress is not None:
                progress.log(f"{pair}: 1h Alpaca rates unavailable", level="warn")
        return

    fill_algospecial_hourly(root, pairs, since, until, out=out, progress=progress)


def _fetch_alpaca_daily(
    root: Path,
    symbols: list[str],
    since: datetime,
    until: datetime,
    *,
    progress: Any | None,
) -> dict[str, list[OhlcvPoint]]:
    out: dict[str, list[OhlcvPoint]] = {}

    def _one(raw: str) -> tuple[str, list[OhlcvPoint] | None]:
        pair = normalize_fx_pair(raw)
        cached = load_cached_ohlcv(root, pair, "1d", since, until)
        if cached:
            return pair, cached
        local = AlpacaForexRatesProvider(allow_synthetic_fallback=False)
        try:
            points = local.fetch("alpaca", pair, "1d", since, until)
        except Exception:  # noqa: BLE001
            return pair, None
        if points and str(getattr(local, "last_source", "")) == "alpaca":
            save_cached_ohlcv(root, pair, "1d", since, until, points)
            return pair, points
        return pair, None

    done = 0
    with ThreadPoolExecutor(max_workers=_FX_WORKERS) as pool:
        futs = [pool.submit(_one, raw) for raw in symbols]
        for fut in as_completed(futs):
            done += 1
            pair, points = fut.result()
            if progress is not None:
                progress.step(done, total=len(symbols), pair=pair)
            if points:
                out[pair] = points
    return out
