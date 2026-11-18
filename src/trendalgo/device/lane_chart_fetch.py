"""Alpaca 1h bar fetch + disk cache for TradFi/FX chart enrich."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from trendalgo.market.ohlcv_disk_cache import load_cached_ohlcv, save_cached_ohlcv
from trendalgo.market.types import OhlcvPoint

_CHUNK = 100


def fetch_lane_1h_bars(
    root: Path,
    pairs: list[str],
    since: datetime,
    until: datetime,
    *,
    lane: str,
    progress: Any | None = None,
) -> dict[str, list[OhlcvPoint]]:
    """Load cached 1h bars; fetch missing via Alpaca / AlgoSpecial (no synthetic FX)."""
    from trendalgo.device.scan_base_ohlcv_forex_fallback import load_covering_cached_ohlcv

    out: dict[str, list[OhlcvPoint]] = {}
    missing: list[str] = []
    eid = (lane or "").strip().lower()
    for i, pair in enumerate(pairs, start=1):
        cached = load_cached_ohlcv(root, pair, "1h", since, until)
        if (not cached or len(cached) < 24) and eid == "forex":
            # Day-bucket keys from the opportunity scan often differ from enrich windows.
            cached = load_covering_cached_ohlcv(root, pair, "1h", since, until, min_bars=24)
        if cached and len(cached) >= 24:
            out[pair] = cached
        else:
            missing.append(pair)
        if progress is not None and i % 25 == 0:
            progress.step(i, total=len(pairs), pair=pair)
    if missing:
        (_fetch_forex if eid == "forex" else _fetch_tradfi)(
            root, missing, since, until, out=out, progress=progress
        )
    if progress is not None:
        progress.step(len(pairs), total=len(pairs), pair="—")
    return out


def _fetch_tradfi(
    root: Path,
    pairs: list[str],
    since: datetime,
    until: datetime,
    *,
    out: dict[str, list[OhlcvPoint]],
    progress: Any | None,
) -> None:
    from trendalgo.market.alpaca_ohlcv import (
        AlpacaOhlcvProvider,
        fetch_alpaca_equity_bars_multi,
        normalize_alpaca_symbol,
    )

    syms = [normalize_alpaca_symbol(p.split("/")[0]) for p in pairs]
    total_pairs = len(pairs)

    def _on_chunk(done: int, total: int, sample: str) -> None:
        if progress is None:
            return
        approx = min(total_pairs, done * _CHUNK)
        progress.step(approx, total=total_pairs, pair=f"{sample}/USD")
        progress.log(f"1h multi-bars chunk {done}/{total} · {sample}")

    try:
        fetched = fetch_alpaca_equity_bars_multi(
            syms, "1h", since, until, chunk_size=_CHUNK, on_chunk=_on_chunk
        )
    except Exception as exc:  # noqa: BLE001
        if progress is not None:
            progress.log(f"1h multi-bars failed ({exc}); per-pair fallback", level="warn")
        fetched, provider = {}, AlpacaOhlcvProvider(allow_synthetic_fallback=False)
        for i, sym in enumerate(syms, start=1):
            if progress is not None:
                progress.step(i, total=len(syms), pair=f"{sym}/USD")
            try:
                pts = provider.fetch("alpaca", f"{sym}/USD", "1h", since, until)
            except Exception:  # noqa: BLE001
                pts = []
            if pts:
                fetched[sym] = pts
    for sym, points in fetched.items():
        if points:
            pair = f"{sym}/USD"
            save_cached_ohlcv(root, pair, "1h", since, until, points)
            out[pair] = points


def _fetch_forex(
    root: Path,
    pairs: list[str],
    since: datetime,
    until: datetime,
    *,
    out: dict[str, list[OhlcvPoint]],
    progress: Any | None,
) -> None:
    from trendalgo.device.forex_bars import fetch_forex_hourly_bars

    fetch_forex_hourly_bars(root, pairs, since, until, out=out, progress=progress)
