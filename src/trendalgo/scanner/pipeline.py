"""Scanner pipeline — live volume, continuous 1h, and optional gain qualification."""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from trendalgo.scanner.config import ScannerSettings
from trendalgo.scanner.listings import verify_kraken_listings
from trendalgo.scanner.live_market import LiveMarketRow, fetch_live_market
from trendalgo.scanner.progress import get_scan_progress
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot


class SnapshotCache(Protocol):
    def latest_successful_snapshot(self) -> QualifiedSnapshot | None: ...


MarketFetcher = Callable[[list[str]], list[LiveMarketRow]]


def _sample_market() -> list[dict[str, float | str]]:
    return [
        {"pair": "BTC/USD", "gain_pct": 0.035, "volume_usd": 5000000},
        {"pair": "ETH/USD", "gain_pct": 0.048, "volume_usd": 2000000},
        {"pair": "SOL/USD", "gain_pct": 0.062, "volume_usd": 800000},
        {"pair": "ADA/USD", "gain_pct": 0.015, "volume_usd": 400000},
        {"pair": "DOT/USD", "gain_pct": 0.028, "volume_usd": 300000},
    ]


def _sample_rows() -> list[LiveMarketRow]:
    return [
        LiveMarketRow(
            pair=str(row["pair"]),
            bars=[],
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
    funnel_out: dict[str, float | int] | None = None,
) -> QualifiedSnapshot:
    from trendalgo.device.portfolio_categories import is_stablecoin_base

    progress = get_scan_progress()
    listed = verify_kraken_listings()
    pairs = [p for p in listed if not is_stablecoin_base(p)]
    skipped_stables = len(listed) - len(pairs)
    progress.log(
        f"Universe: {len(pairs)} Kraken spot bases (canonical pairs; filter: {settings.universe_filter})"
    )
    if skipped_stables:
        progress.log(f"Excluded {skipped_stables} stablecoin pair(s)")
    use_sample = sample or os.environ.get("TRENDALGO_MARKET_SOURCE", "").lower() == "synthetic"
    if use_sample:
        progress.log("Using synthetic sample market (not live Kraken data)", level="warn")
    degraded = use_sample
    activity_funnel: dict[str, float | int] = {}
    require_cont = bool(getattr(settings, "require_continuous_1h", True))
    live_fetcher: MarketFetcher = fetcher or (
        lambda ps: fetch_live_market(
            ps,
            min_volume_usd=settings.min_volume_usd,
            min_gain_pct=settings.min_gain_pct,
            min_gain_7d_pct=float(getattr(settings, "min_gain_7d_pct", 0.0) or 0.0),
            require_continuous_1h=require_cont,
            funnel_out=activity_funnel,
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
    after_pipeline_vol = 0
    progress.phase("Scan · rank by gain / volume", total=len(market), unit="pairs")
    for row in market:
        pair = row.pair
        if pair not in pairs:
            continue
        gain = row.gain_pct
        volume_usd = row.volume_usd
        if volume_usd < settings.min_volume_usd:
            continue
        # min_gain_pct <= 0 disables the gain gate (volume-first device scans).
        if settings.min_gain_pct > 0 and gain < settings.min_gain_pct:
            continue
        after_pipeline_vol += 1
        gain_ok = settings.min_gain_pct <= 0 or gain >= settings.min_gain_pct
        candidates.append(
            OpportunityRow(
                rank=0,
                pair=pair,
                uniformity=0.0,  # unused schema field (board no longer scores uniformity)
                gain_pct=gain,
                # Store approximate 24h notional USD (bridge maps this to volume_24h).
                volume_score=float(volume_usd),
                entry_signal=gain_ok,
                sparkline=[],
            )
        )

    progress.step(len(market), total=len(market))
    candidates.sort(key=lambda o: (o.gain_pct, o.volume_score), reverse=True)
    progress.log(f"Qualified {len(candidates)} of {len(market)} pairs (volume / activity board)")
    ranked = [
        OpportunityRow(rank=i + 1, **{k: v for k, v in o.model_dump().items() if k != "rank"})
        for i, o in enumerate(candidates)
    ]

    now = datetime.now(UTC)
    as_of = max((row.as_of for row in market), default=now)
    after_vol_n = int(activity_funnel.get("after_volume_n") or after_pipeline_vol)
    after_act_n = int(activity_funnel.get("after_activity_n") or after_pipeline_vol)
    if funnel_out is not None:
        funnel_out.clear()
        funnel_out.update(
            {
                "listed_n": len(pairs),
                "after_volume_n": after_vol_n,
                "after_activity_n": after_act_n,
                "qualified_n": len(ranked),
                "min_volume_usd": float(settings.min_volume_usd),
                "require_continuous_1h": 1 if require_cont else 0,
            }
        )
    return QualifiedSnapshot(
        generated_at=now,
        as_of=as_of,
        scan_id=0,
        degraded=degraded,
        opportunities=ranked,
    )
