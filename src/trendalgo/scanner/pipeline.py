"""Scanner pipeline — live volume, gain, and uniformity qualification."""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from trendalgo.lts.adapter import OhlcvBar
from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner.config import ScannerSettings
from trendalgo.scanner.listings import verify_kraken_listings
from trendalgo.scanner.live_market import LiveMarketRow, fetch_live_market
from trendalgo.scanner.progress import get_scan_progress
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot
from trendalgo.scanner.uniformity import uniformity_score


class SnapshotCache(Protocol):
    def latest_successful_snapshot(self) -> QualifiedSnapshot | None: ...


MarketFetcher = Callable[[list[str]], list[LiveMarketRow]]


def _synthetic_bars(gain_pct: float, base: float = 100.0) -> list[OhlcvPoint]:
    """Build trending bars for uniformity when live OHLCV unavailable."""
    bars: list[OhlcvPoint] = []
    step = gain_pct / 20 if gain_pct else 0.001
    price = base
    ts = int(datetime.now(UTC).timestamp()) - (24 * 300)
    for i in range(25):
        price *= 1 + step
        bars.append(
            OhlcvPoint(
                time=ts + i * 300,
                open=price,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=1000,
            )
        )
    return bars


def _sample_market() -> list[dict[str, float | str]]:
    return [
        {"pair": "BTC/USD", "gain_pct": 0.035, "volume_usd": 5000000, "base": 50000},
        {"pair": "ETH/USD", "gain_pct": 0.048, "volume_usd": 2000000, "base": 3000},
        {"pair": "SOL/USD", "gain_pct": 0.062, "volume_usd": 800000, "base": 150},
        {"pair": "ADA/USD", "gain_pct": 0.015, "volume_usd": 400000, "base": 0.5},
        {"pair": "DOT/USD", "gain_pct": 0.028, "volume_usd": 300000, "base": 8},
    ]


def _sample_rows() -> list[LiveMarketRow]:
    return [
        LiveMarketRow(
            pair=str(row["pair"]),
            bars=_synthetic_bars(float(row["gain_pct"]), float(row["base"])),
            gain_pct=float(row["gain_pct"]),
            volume_usd=float(row["volume_usd"]),
        )
        for row in _sample_market()
    ]


def run_pipeline(
    settings: ScannerSettings,
    *,
    store: SnapshotCache | None = None,
    sample: bool = False,
    fetcher: MarketFetcher | None = None,
) -> QualifiedSnapshot:
    progress = get_scan_progress()
    pairs = verify_kraken_listings()
    progress.log(f"Universe: {len(pairs)} Kraken USD pairs (filter: {settings.universe_filter})")
    use_sample = sample or os.environ.get("TRENDALGO_MARKET_SOURCE", "").lower() == "synthetic"
    if use_sample:
        progress.log("Using synthetic sample market (not live Kraken data)", level="warn")
    degraded = use_sample
    live_fetcher: MarketFetcher = fetcher or (
        lambda ps: fetch_live_market(
            ps,
            min_volume_usd=settings.min_volume_usd,
            min_gain_pct=settings.min_gain_pct,
            min_gain_7d_pct=float(getattr(settings, "min_gain_7d_pct", 0.0) or 0.0),
        )
    )
    try:
        market = _sample_rows() if use_sample else live_fetcher(pairs)
    except Exception as exc:
        progress.log(f"Live market fetch failed: {exc}", level="error")
        if use_sample:
            market = _sample_rows()
            degraded = True
        else:
            cached = store.latest_successful_snapshot() if store else None
            if cached is not None:
                progress.log(
                    "Reusing last successful scan (live Kraken fetch failed)",
                    level="warn",
                )
                # Keep the prior snapshot as-is (not marked degraded) so the device can refresh.
                return cached
            raise RuntimeError(f"Kraken market data was not available ({exc})") from exc

    candidates: list[OpportunityRow] = []
    progress.phase("Scan · uniformity gate + rank", total=len(market), unit="pairs")
    for row in market:
        pair = row.pair
        if pair not in pairs:
            continue
        gain = row.gain_pct
        volume_usd = row.volume_usd
        if volume_usd < settings.min_volume_usd or gain < settings.min_gain_pct:
            continue
        bars = [
            OhlcvBar(
                timestamp_ms=b.time * 1000,
                open=b.open,
                high=b.high,
                low=b.low,
                close=b.close,
                volume=b.volume,
            )
            for b in row.bars
        ]
        uni = uniformity_score(bars)
        if uni < settings.min_uniformity:
            continue
        spark = [round(b.close, 2) for b in bars[-12:]]
        entry = uni >= settings.min_uniformity and gain >= settings.min_gain_pct
        candidates.append(
            OpportunityRow(
                rank=0,
                pair=pair,
                uniformity=uni,
                gain_pct=gain,
                # Store approximate 24h notional USD (bridge maps this to volume_24h).
                volume_score=float(volume_usd),
                entry_signal=entry,
                sparkline=spark,
            )
        )

    progress.step(len(market), total=len(market))
    candidates.sort(key=lambda o: (o.uniformity, o.gain_pct), reverse=True)
    progress.log(
        f"Qualified {len(candidates)} of {len(market)} pairs "
        f"(uniformity ≥ {settings.min_uniformity:.2f})"
    )
    ranked = [
        OpportunityRow(rank=i + 1, **{k: v for k, v in o.model_dump().items() if k != "rank"})
        for i, o in enumerate(candidates)
    ]

    now = datetime.now(UTC)
    as_of = max((row.as_of for row in market), default=now)
    return QualifiedSnapshot(
        generated_at=now,
        as_of=as_of,
        scan_id=0,
        degraded=degraded,
        opportunities=ranked,
    )
