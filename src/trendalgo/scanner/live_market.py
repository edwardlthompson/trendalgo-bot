"""Live OHLCV acquisition for scanner runs (volume → gain → uniformity bars)."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from trendalgo.market.kraken import fetch_ohlcv, fetch_quote_volumes
from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner.progress import get_scan_progress

# Extended 1h window: 24h volume + optional 7d gain from the same fetch.
_HOUR_LOOKBACK = timedelta(days=8)


@dataclass(frozen=True)
class LiveMarketRow:
    pair: str
    bars: list[OhlcvPoint]
    gain_pct: float
    volume_usd: float

    @property
    def as_of(self) -> datetime:
        if not self.bars:
            return datetime.now(UTC)
        return datetime.fromtimestamp(self.bars[-1].time, tz=UTC)


def _max_workers() -> int:
    raw = os.environ.get("TRENDALGO_LIVE_MARKET_WORKERS", "").strip()
    if raw:
        try:
            return max(1, min(16, int(raw)))
        except ValueError:
            pass
    return 12


def _prune_pairs_by_ticker_volume(
    pairs: list[str],
    *,
    min_volume_usd: float,
    timeout_ms: int,
) -> list[str]:
    """Drop obvious low-volume pairs via ticker quoteVolume before 1h OHLCV."""
    progress = get_scan_progress()
    if min_volume_usd <= 0 or not pairs:
        return list(pairs)
    try:
        volumes = fetch_quote_volumes(pairs, timeout_ms=timeout_ms)
    except Exception as exc:
        progress.log(f"Ticker volume prefilter skipped ({exc})", level="warn")
        return list(pairs)
    if not volumes:
        progress.log("Ticker volume prefilter returned no rows; using full universe", level="warn")
        return list(pairs)
    kept = [p for p in pairs if volumes.get(p, 0.0) >= min_volume_usd]
    progress.log(
        f"Ticker prefilter: {len(kept)} of {len(pairs)} pairs ≥ ${min_volume_usd / 1e6:.2f}M 24h"
    )
    return kept


def fetch_live_market(
    pairs: list[str],
    *,
    min_volume_usd: float = 0.0,
    min_gain_pct: float = 0.0,
    min_gain_7d_pct: float = 0.0,
    timeout_seconds: float = 12.0,
    max_retries: int = 2,
    backoff_seconds: float = 0.25,
) -> list[LiveMarketRow]:
    """Fetch scanner universe in staged gates (partial failures OK).

    1. Hourly OHLCV (~8d) → 24h volume + optional 7d gain; drop under floors.
    2. Daily OHLCV → 30d gain on survivors; drop under ``min_gain_pct``.
    3. 5m bars on survivors (uniformity gate runs in the pipeline).
    """
    until = datetime.now(UTC)
    hour_since = until - _HOUR_LOOKBACK
    day_since = until - timedelta(days=40)
    five_since = until - timedelta(hours=3)
    timeout_ms = max(1, int(timeout_seconds * 1000))
    progress = get_scan_progress()
    errors: list[str] = []

    pairs = _prune_pairs_by_ticker_volume(
        pairs,
        min_volume_usd=min_volume_usd,
        timeout_ms=timeout_ms,
    )
    workers = min(_max_workers(), max(1, len(pairs)))
    if not pairs:
        return []

    volumes = _phase_volume(
        pairs,
        hour_since=hour_since,
        until=until,
        workers=workers,
        timeout_ms=timeout_ms,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
        errors=errors,
    )
    if not volumes:
        detail = "; ".join(errors[:5]) if errors else "no pairs"
        raise RuntimeError(f"live OHLCV fetch failed for all pairs ({detail})")

    after_vol = [(p, v, g7) for p, v, g7 in volumes if v >= min_volume_usd]
    progress.log(
        f"{len(after_vol)} of {len(volumes)} pairs pass volume ≥ ${min_volume_usd / 1e6:.2f}M"
    )
    if min_gain_7d_pct > 0:
        before = len(after_vol)
        after_vol = [(p, v, g7) for p, v, g7 in after_vol if g7 >= min_gain_7d_pct]
        progress.log(
            f"{len(after_vol)} of {before} pairs pass 7d gain ≥ {min_gain_7d_pct * 100:.1f}%"
        )
    if not after_vol:
        return []

    vol_passers = [(p, v) for p, v, _g7 in after_vol]
    gains = _phase_gain(
        vol_passers,
        day_since=day_since,
        until=until,
        workers=min(workers, max(1, len(vol_passers))),
        timeout_ms=timeout_ms,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
        errors=errors,
    )
    after_gain = [(p, v, g) for p, v, g in gains if g >= min_gain_pct]
    progress.log(
        f"{len(after_gain)} of {len(gains)} pairs pass 30d gain ≥ {min_gain_pct * 100:.1f}%"
    )
    if not after_gain:
        return []

    rows = _phase_five_minute(
        after_gain,
        five_since=five_since,
        until=until,
        workers=min(workers, max(1, len(after_gain))),
        timeout_ms=timeout_ms,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
        errors=errors,
    )
    order = {p: i for i, p in enumerate(pairs)}
    rows.sort(key=lambda r: order.get(r.pair, 10_000))
    return rows


def _phase_volume(
    pairs: list[str],
    *,
    hour_since: datetime,
    until: datetime,
    workers: int,
    timeout_ms: int,
    max_retries: int,
    backoff_seconds: float,
    errors: list[str],
) -> list[tuple[str, float, float]]:
    """Return (pair, volume_usd_24h, gain_7d_fraction) from one 1h fetch."""
    progress = get_scan_progress()
    progress.phase("Scan 1/3 · volume", total=len(pairs), unit="pairs")
    out: list[tuple[str, float, float]] = []
    done = 0

    def one(pair: str) -> tuple[str, float, float]:
        return pair, *_fetch_volume_and_gain7d(
            pair,
            hour_since=hour_since,
            until=until,
            timeout_ms=timeout_ms,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, pair): pair for pair in pairs}
        for fut in as_completed(futures):
            pair = futures[fut]
            done += 1
            try:
                p, vol, g7 = fut.result()
                out.append((p, vol, g7))
                progress.log(f"{pair}: 24h vol ${vol / 1e6:.2f}M · 7d {g7 * 100:+.1f}%")
            except Exception as exc:
                errors.append(f"{pair}:{exc}")
                progress.log(f"{pair}: skipped ({exc})", level="warn")
            progress.step(done, total=len(pairs))
    return out


def _phase_gain(
    volume_passers: list[tuple[str, float]],
    *,
    day_since: datetime,
    until: datetime,
    workers: int,
    timeout_ms: int,
    max_retries: int,
    backoff_seconds: float,
    errors: list[str],
) -> list[tuple[str, float, float]]:
    progress = get_scan_progress()
    progress.phase("Scan 2/3 · 30d gain", total=len(volume_passers), unit="pairs")
    out: list[tuple[str, float, float]] = []
    done = 0

    def one(item: tuple[str, float]) -> tuple[str, float, float]:
        pair, vol = item
        gain = _fetch_gain(
            pair,
            day_since=day_since,
            until=until,
            timeout_ms=timeout_ms,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )
        return pair, vol, gain

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, item): item[0] for item in volume_passers}
        for fut in as_completed(futures):
            pair = futures[fut]
            done += 1
            try:
                p, vol, gain = fut.result()
                out.append((p, vol, gain))
                progress.log(f"{pair}: 30d gain {gain * 100:+.1f}%")
            except Exception as exc:
                errors.append(f"{pair}:gain:{exc}")
                progress.log(f"{pair}: no 30d gain ({exc})", level="warn")
            progress.step(done, total=len(volume_passers))
    return out


def _phase_five_minute(
    gain_passers: list[tuple[str, float, float]],
    *,
    five_since: datetime,
    until: datetime,
    workers: int,
    timeout_ms: int,
    max_retries: int,
    backoff_seconds: float,
    errors: list[str],
) -> list[LiveMarketRow]:
    progress = get_scan_progress()
    progress.phase("Scan 3/3 · 5m bars for uniformity", total=len(gain_passers), unit="pairs")
    rows: list[LiveMarketRow] = []
    done = 0

    def one(item: tuple[str, float, float]) -> LiveMarketRow:
        pair, vol, gain = item
        bars = _fetch_five_minute_bars(
            pair,
            five_since,
            until,
            timeout_ms=timeout_ms,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )
        return LiveMarketRow(pair=pair, bars=bars, gain_pct=gain, volume_usd=vol)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(one, item): item[0] for item in gain_passers}
        for fut in as_completed(futures):
            pair = futures[fut]
            done += 1
            try:
                rows.append(fut.result())
                progress.log(f"{pair}: {len(rows[-1].bars)} 5m bars")
            except Exception as exc:
                errors.append(f"{pair}:uni:{exc}")
                progress.log(f"{pair}: no 5m bars ({exc})", level="warn")
            progress.step(done, total=len(gain_passers))
    return rows


def _fetch_volume_and_gain7d(
    pair: str,
    *,
    hour_since: datetime,
    until: datetime,
    timeout_ms: int,
    max_retries: int,
    backoff_seconds: float,
) -> tuple[float, float]:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            hourly = fetch_ohlcv(pair, "1h", hour_since, until, timeout_ms=timeout_ms)
            if len(hourly) < 2:
                raise RuntimeError(f"insufficient hourly OHLCV for {pair}")
            vol_window = hourly[-24:] if len(hourly) >= 24 else hourly
            volume = sum(float(b.volume) * float(b.close) for b in vol_window)
            gain7 = _gain_from_closes([float(b.close) for b in hourly], bars=168)
            return volume, gain7
        except Exception as exc:
            last_error = exc
            if attempt + 1 < max_retries:
                time.sleep(backoff_seconds * (2**attempt))
    raise last_error or RuntimeError(f"volume OHLCV failed for {pair}")


def _gain_from_closes(closes: list[float], *, bars: int) -> float:
    window = closes[-bars:] if len(closes) >= bars else closes
    if len(window) < 2:
        return 0.0
    first, last = window[0], window[-1]
    if first <= 0:
        return 0.0
    return (last / first) - 1.0


def _fetch_gain(
    pair: str,
    *,
    day_since: datetime,
    until: datetime,
    timeout_ms: int,
    max_retries: int,
    backoff_seconds: float,
) -> float:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            daily = fetch_ohlcv(pair, "1d", day_since, until, timeout_ms=timeout_ms)[-35:]
            if len(daily) < 2:
                raise RuntimeError(f"insufficient daily OHLCV for {pair}")
            gain_window = daily[-30:] if len(daily) >= 30 else daily
            first, last = float(gain_window[0].close), float(gain_window[-1].close)
            if first <= 0:
                raise RuntimeError(f"invalid daily OHLCV for {pair}")
            return (last / first) - 1.0
        except Exception as exc:
            last_error = exc
            if attempt + 1 < max_retries:
                time.sleep(backoff_seconds * (2**attempt))
    raise last_error or RuntimeError(f"gain OHLCV failed for {pair}")


def _fetch_five_minute_bars(
    pair: str,
    since: datetime,
    until: datetime,
    *,
    timeout_ms: int,
    max_retries: int,
    backoff_seconds: float,
) -> list[OhlcvPoint]:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            bars = fetch_ohlcv(pair, "5m", since, until, timeout_ms=timeout_ms)[-25:]
            if len(bars) < 2:
                raise RuntimeError(f"insufficient 5m OHLCV for {pair}")
            return bars
        except Exception as exc:
            last_error = exc
            if attempt + 1 < max_retries:
                time.sleep(backoff_seconds * (2**attempt))
    raise last_error or RuntimeError(f"5m OHLCV failed for {pair}")
