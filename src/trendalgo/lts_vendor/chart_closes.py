"""Fetch real 1h / 1d closes for LTS Scanner sparklines (no synthetic fills).

The same 1h bars also feed Vol Δ% (``scanner/volume_acceleration.py``), so the
dashboard's volume column costs no extra exchange calls.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from typing import Any

from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner.progress import get_scan_progress
from trendalgo.scanner.volume_acceleration import apply_volume_acceleration

FetchOhlcv = Callable[..., list[OhlcvPoint]]

_HOUR_CAP = 30 * 24
_DAY_CAP = 35


def gain_pct_from_closes(closes: list[float]) -> float | None:
    """Percent change first→last close (LTS gains.* scale, e.g. 1.3 = +1.3%)."""
    if len(closes) < 2:
        return None
    first, last = closes[0], closes[-1]
    if first <= 0 or not (first == first and last == last):
        return None
    return ((last / first) - 1.0) * 100.0


def closes_from_bars(bars: list[OhlcvPoint], *, cap: int) -> list[float]:
    nums = [float(b.close) for b in bars if b.close == b.close]
    if len(nums) > cap:
        nums = nums[-cap:]
    return nums


def _chart_workers() -> int:
    raw = os.environ.get("TRENDALGO_CHART_WORKERS", "").strip()
    if raw:
        try:
            return max(1, min(16, int(raw)))
        except ValueError:
            pass
    return 8


def _fetch_bars(
    pair: str,
    timeframe: str,
    *,
    fetcher: FetchOhlcv,
    until: datetime,
    attempts: int = 3,
) -> list[OhlcvPoint]:
    """Raw bars for 1h (31 days) or 1d (40 days); empty list on soft-fail."""
    last: list[OhlcvPoint] = []
    for i in range(max(1, attempts)):
        try:
            if timeframe == "1h":
                bars = fetcher(pair, "1h", until - timedelta(days=31), until, timeout_ms=20_000)
            else:
                bars = fetcher(pair, "1d", until - timedelta(days=40), until, timeout_ms=20_000)
            last = list(bars)
            if last:
                return last
        except Exception:
            last = []
        if i + 1 < attempts:
            time.sleep(0.35 * (i + 1))
    return last


def _fetch_tf(
    pair: str,
    timeframe: str,
    *,
    fetcher: FetchOhlcv,
    until: datetime,
    attempts: int = 3,
) -> list[float]:
    cap = _HOUR_CAP if timeframe == "1h" else _DAY_CAP
    bars = _fetch_bars(pair, timeframe, fetcher=fetcher, until=until, attempts=attempts)
    return closes_from_bars(bars, cap=cap)


def fetch_chart_closes_for_pair(
    pair: str,
    *,
    fetch_ohlcv: FetchOhlcv | None = None,
    now: datetime | None = None,
) -> tuple[list[float], list[float]]:
    """Return (closes_1h, closes_1d). Empty lists on soft-fail."""
    from trendalgo.market.kraken import fetch_ohlcv as default_fetch

    fetcher = fetch_ohlcv or default_fetch
    until = now or datetime.now(UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    return (
        _fetch_tf(pair, "1h", fetcher=fetcher, until=until),
        _fetch_tf(pair, "1d", fetcher=fetcher, until=until),
    )


def _apply_closes(coin: dict[str, Any], h1: list[float], d1: list[float]) -> None:
    if h1:
        coin["closes_1h"] = h1
    else:
        coin.pop("closes_1h", None)
    if d1:
        coin["closes_1d"] = d1
    else:
        coin.pop("closes_1d", None)
    g7 = gain_pct_from_closes(h1[-168:]) if len(h1) >= 168 else gain_pct_from_closes(h1)
    g30 = gain_pct_from_closes(d1[-30:]) if len(d1) >= 2 else None
    if g30 is None and len(h1) >= 2:
        g30 = gain_pct_from_closes(h1)
    gains = dict(coin.get("gains") or {})
    if g7 is not None:
        gains["7d"] = round(g7, 6)
    if g30 is not None:
        gains["30d"] = round(g30, 6)
    if gains:
        coin["gains"] = gains
    coin["ohlcv_source"] = "kraken"
    identity = dict(coin.get("identity") or {})
    identity["ohlcv_source"] = "kraken"
    coin["identity"] = identity


def attach_chart_closes(
    coins: list[dict[str, Any]],
    pair_for_symbol: Callable[[str], str],
    *,
    fetch_ohlcv: FetchOhlcv | None = None,
) -> list[dict[str, Any]]:
    """Mutate coin dicts: real closes, gains from those series, and Vol Δ% from 1h volume."""
    from trendalgo.market.kraken import fetch_ohlcv as default_fetch

    fetcher = fetch_ohlcv or default_fetch
    progress = get_scan_progress()
    until = datetime.now(UTC)
    symbols: list[tuple[dict[str, Any], str]] = []
    for coin in coins:
        symbol = str(coin.get("symbol", "")).upper()
        if symbol:
            symbols.append((coin, pair_for_symbol(symbol)))
    unique_pairs = list(dict.fromkeys(pair for _, pair in symbols))
    # Skip 1h fetch when the coin already has a usable spark series from the scan.
    need_1h: set[str] = set()
    for coin, pair in symbols:
        closes = coin.get("chart_closes_1h") or coin.get("spark_closes_7d") or []
        if not isinstance(closes, list) or len(closes) < 24:
            need_1h.add(pair)
    jobs = [(pair, "1d") for pair in unique_pairs] + [(p, "1h") for p in need_1h]
    bars: dict[tuple[str, str], list[OhlcvPoint]] = {}
    if jobs:
        progress.phase("Enrich · chart closes + Vol Δ%", total=len(unique_pairs), unit="pairs")
        with ThreadPoolExecutor(max_workers=min(_chart_workers(), len(jobs))) as pool:
            futs = {
                pool.submit(_fetch_bars, pair, tf, fetcher=fetcher, until=until): (pair, tf)
                for pair, tf in jobs
            }
            hourly_done = 0
            for fut in as_completed(futs):
                key = futs[fut]
                try:
                    bars[key] = fut.result()
                except Exception:
                    bars[key] = []
                if key[1] == "1h":
                    hourly_done += 1
                    progress.step(hourly_done)
    vol_ok = 0
    for coin, pair in symbols:
        h1 = bars.get((pair, "1h"), [])
        d1 = bars.get((pair, "1d"), [])
        if pair not in need_1h:
            existing = coin.get("chart_closes_1h") or coin.get("closes_1h") or []
            h_closes = [float(x) for x in existing if isinstance(x, (int, float))][:_HOUR_CAP]
        else:
            h_closes = closes_from_bars(h1, cap=_HOUR_CAP)
        _apply_closes(coin, h_closes, closes_from_bars(d1, cap=_DAY_CAP))
        if h_closes:
            from trendalgo.lts_vendor.utils.scan_artifacts import risk_context_from_hourly_closes

            rc = risk_context_from_hourly_closes(h_closes)
            if rc:
                coin["risk_context"] = rc
        symbol = str(coin.get("symbol", "")).upper()
        if apply_volume_acceleration(coin, h1):
            vol_ok += 1
            progress.log(
                f"{symbol}: Vol Δ {float(coin['volume_acceleration_pct']):+.1f}% "
                f"vs {coin['volume_acceleration_window_days']}-day baseline ({len(h1)} 1h bars)"
            )
        else:
            progress.log(f"{symbol}: Vol Δ unavailable ({len(h1)} 1h bars)", level="warn")
    if symbols:
        progress.set_counts(coins=len(symbols), vol_delta_ok=vol_ok)
    return coins
