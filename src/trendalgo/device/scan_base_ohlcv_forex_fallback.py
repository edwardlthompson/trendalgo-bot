"""Forex All-TA/MC bars when Alpaca FX is denied: disk cache reuse + AlgoSpecial H1."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from trendalgo.brokers.forex_universe import normalize_fx_pair
from trendalgo.market.algospecial_forex import (
    AlgoSpecialUnsupportedError,
    fetch_algospecial_h1,
)
from trendalgo.market.algospecial_fx_unsupported import load_unsupported
from trendalgo.market.ohlcv_disk_cache import load_cached_ohlcv, save_cached_ohlcv
from trendalgo.market.types import OhlcvPoint


def normalize_fx_cache_pair(symbol: str, pair: str) -> str:
    raw = str(pair or symbol or "").strip().upper()
    if not raw:
        return ""
    return normalize_fx_pair(raw)


def load_covering_cached_ohlcv(
    root: Path,
    pair: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    min_bars: int = 24,
) -> list[OhlcvPoint] | None:
    """Reuse any same-pair/tf day-bucket cache that overlaps the requested window."""
    exact = load_cached_ohlcv(root, pair, timeframe, since, until)
    if exact and len(exact) >= min_bars:
        return exact
    cache_dir = root / "ohlcv_cache"
    if not cache_dir.is_dir():
        return None
    safe = pair.replace("/", "_").upper()
    prefix = f"{safe}_{timeframe}_"
    since_ts = int(since.timestamp())
    until_ts = int(until.timestamp())
    best: list[OhlcvPoint] | None = None
    best_n = 0
    for path in cache_dir.glob(f"{prefix}*.json"):
        # Parse bars via exact loader by reconstructing since/until from filename.
        # EUR_USD_1h_20261009_20261118.json
        stem = path.stem
        if not stem.startswith(prefix):
            continue
        tail = stem[len(prefix) :]
        parts = tail.split("_")
        if len(parts) != 2 or len(parts[0]) != 8 or len(parts[1]) != 8:
            continue
        try:
            file_since = datetime.strptime(parts[0], "%Y%m%d").replace(tzinfo=UTC)
            file_until = datetime.strptime(parts[1], "%Y%m%d").replace(tzinfo=UTC)
        except ValueError:
            continue
        points = load_cached_ohlcv(root, pair, timeframe, file_since, file_until)
        if not points:
            continue
        clipped = [p for p in points if since_ts <= int(p.time) <= until_ts]
        if len(clipped) < min_bars:
            clipped = points  # keep full series if wall-clock trim is sparse
        if len(clipped) > best_n:
            best = clipped
            best_n = len(clipped)
    return best if best_n >= min_bars else None


def fetch_forex_h1_algospecial(
    root: Path | None,
    pair: str,
    since: datetime,
    until: datetime,
) -> list[OhlcvPoint] | None:
    """Live AlgoSpecial H1 when Alpaca FX is unavailable."""
    fx = normalize_fx_pair(pair)
    if root is not None and fx in load_unsupported(root):
        return None
    try:
        points = fetch_algospecial_h1(fx, since, until)
    except AlgoSpecialUnsupportedError:
        if root is not None:
            from trendalgo.market.algospecial_fx_unsupported import mark_unsupported

            mark_unsupported(root, fx)
        return None
    except Exception:  # noqa: BLE001
        return None
    if not points:
        return None
    if root is not None:
        save_cached_ohlcv(root, fx, "1h", since, until, points)
    return points
