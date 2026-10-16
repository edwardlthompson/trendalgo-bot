"""Dynamic pair forager — live public market when available (T25, T28)."""

from __future__ import annotations

import os
import threading
import time
from datetime import UTC, datetime
from typing import Any, cast

from trendalgo.scanner.config import ScannerSettings, default_scanner_settings
from trendalgo.scanner.listings import verify_kraken_listings
from trendalgo.scanner.live_market import fetch_live_market
from trendalgo.scanner.pipeline import _sample_market

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, Any] | None = None
_CACHE_AT = 0.0
_CACHE_TTL_S = 300.0


def _cache_ttl_s() -> float:
    raw = os.environ.get("TRENDALGO_FORAGER_CACHE_TTL_S", "").strip()
    if not raw:
        return _CACHE_TTL_S
    try:
        return max(0.0, float(raw))
    except ValueError:
        return _CACHE_TTL_S


def forage_pairs(
    settings: ScannerSettings | None = None,
    *,
    top_n: int = 8,
    force_refresh: bool = False,
) -> dict[str, object]:
    """Rank tradable pairs by volume and momentum heuristics."""
    global _CACHE, _CACHE_AT
    ttl = _cache_ttl_s()
    if not force_refresh and ttl > 0:
        with _CACHE_LOCK:
            if _CACHE is not None and (time.monotonic() - _CACHE_AT) < ttl:
                return dict(_CACHE)

    settings = settings or default_scanner_settings()
    listings = set(verify_kraken_listings())
    use_sample = os.environ.get("TRENDALGO_MARKET_SOURCE", "").lower() == "synthetic"
    rows: list[dict[str, float | str]] = []
    source = "lts_volume_heuristic"
    if use_sample:
        rows = list(_sample_market())
        source = "synthetic_sample"
    else:
        try:
            live = fetch_live_market(sorted(listings)[: max(top_n * 3, 15)])
            rows = [
                {
                    "pair": r.pair,
                    "gain_pct": r.gain_pct,
                    "volume_usd": r.volume_usd,
                }
                for r in live
            ]
            source = "kraken_public_ohlcv"
        except Exception:
            rows = list(_sample_market())
            source = "synthetic_fallback"

    scored: list[dict[str, object]] = []
    for row in rows:
        pair = str(row["pair"])
        if pair not in listings:
            continue
        gain = float(row["gain_pct"])
        volume_usd = float(row["volume_usd"])
        if volume_usd < settings.min_volume_usd * 0.5:
            continue
        volume_score = min(1.0, volume_usd / max(settings.min_volume_usd, 1))
        momentum_score = min(1.0, gain / max(settings.min_gain_pct, 0.001))
        composite = round(0.6 * volume_score + 0.4 * momentum_score, 4)
        scored.append(
            {
                "pair": pair,
                "volume_usd": volume_usd,
                "gain_pct": gain,
                "volume_score": round(volume_score, 4),
                "momentum_score": round(momentum_score, 4),
                "forager_score": composite,
                "source": source,
            }
        )

    scored.sort(
        key=lambda r: float(cast(float | int | str, r.get("forager_score", 0))), reverse=True
    )
    picks = scored[:top_n]
    payload: dict[str, object] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "pair_count": len(picks),
        "pairs": picks,
        "prototype": source != "kraken_public_ohlcv",
        "degraded": source != "kraken_public_ohlcv",
    }
    if ttl > 0:
        with _CACHE_LOCK:
            _CACHE = dict(payload)
            _CACHE_AT = time.monotonic()
    return payload
