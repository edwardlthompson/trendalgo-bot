"""Per-venue spot universe + live market fetch (authenticated ccxt)."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

from trendalgo.device.portfolio_categories import is_stablecoin_base
from trendalgo.exchanges.private_budget import acquire_private_slot
from trendalgo.exchanges.private_client import ccxt_client
from trendalgo.exchanges.registry import ExchangeEntry
from trendalgo.lts.adapter import OhlcvBar
from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner.config import ScannerSettings
from trendalgo.scanner.listings import _SKIP_BASES, pick_canonical_pair
from trendalgo.scanner.progress import get_scan_progress
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot
from trendalgo.scanner.uniformity import uniformity_score


def _slot(entry: ExchangeEntry) -> None:
    if not acquire_private_slot(entry.id, max_per_min=entry.max_private_calls_per_min):
        raise RuntimeError(f"private_rate_budget_exhausted:{entry.id}")


def list_canonical_pairs(entry: ExchangeEntry, client: Any) -> list[str]:
    """Active spot pairs for venue, one canonical quote per base."""
    _slot(entry)
    markets = client.load_markets()
    preferred = str(entry.quote_currency or "USD").upper()
    aliases = {a.upper() for a in (entry.usd_aliases or ())} | {preferred, "USD", "ZUSD"}
    by_base: dict[str, list[str]] = {}
    for symbol, market in markets.items():
        if not isinstance(market, dict):
            continue
        if not market.get("spot", True):
            continue
        if market.get("active") is False:
            continue
        base = str(market.get("base") or "").upper()
        quote = str(market.get("quote") or "").upper()
        if not base or base in _SKIP_BASES or is_stablecoin_base(base):
            continue
        # Prefer preferred quote family; still keep other quotes for canonical pick.
        pair = symbol.upper() if "/" in symbol else f"{base}/{quote}"
        by_base.setdefault(base, []).append(pair)
    out: list[str] = []
    for base in sorted(by_base):
        # Bias pick_canonical toward venue preferred quote by listing it first when present.
        cands = by_base[base]
        preferred_pairs = [p for p in cands if p.split("/", 1)[-1] in aliases]
        ordered = preferred_pairs + [p for p in cands if p not in preferred_pairs]
        chosen = pick_canonical_pair(ordered)
        if chosen:
            out.append(chosen)
    return out


def _ticker_usd_volume(ticker: dict[str, Any]) -> float:
    qv = ticker.get("quoteVolume")
    if qv is not None:
        try:
            return float(qv)
        except (TypeError, ValueError):
            pass
    last = ticker.get("last") or ticker.get("close")
    bv = ticker.get("baseVolume")
    try:
        if last is not None and bv is not None:
            return float(last) * float(bv)
    except (TypeError, ValueError):
        pass
    return 0.0


def fetch_venue_volumes(entry: ExchangeEntry, client: Any, pairs: list[str]) -> dict[str, float]:
    _slot(entry)
    raw = client.fetch_tickers()
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for pair in pairs:
        ticker = raw.get(pair)
        if not isinstance(ticker, dict):
            # Try bare symbol match.
            continue
        out[pair] = _ticker_usd_volume(ticker)
    return out


def _fetch_ohlcv_points(
    entry: ExchangeEntry,
    client: Any,
    pair: str,
    timeframe: str,
    since: datetime,
    until: datetime,
) -> list[OhlcvPoint]:
    _slot(entry)
    since_ms = int(since.timestamp() * 1000)
    rows = client.fetch_ohlcv(pair, timeframe, since=since_ms, limit=720)
    points: list[OhlcvPoint] = []
    for row in rows or []:
        ts_sec = int(row[0] // 1000)
        if ts_sec < int(since.timestamp()) or ts_sec > int(until.timestamp()):
            continue
        points.append(
            OhlcvPoint(
                time=ts_sec,
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
        )
    points.sort(key=lambda p: p.time)
    return points


def run_venue_pipeline(
    settings: ScannerSettings,
    entry: ExchangeEntry,
    *,
    client: Any | None = None,
) -> QualifiedSnapshot:
    """Qualify pairs on one keyed venue; stamps progress with venue id."""
    progress = get_scan_progress()
    progress.log(f"Venue {entry.id}: loading markets (uses your API quota)")
    ex = client or ccxt_client(entry)
    pairs = list_canonical_pairs(entry, ex)
    progress.log(f"Venue {entry.id}: {len(pairs)} spot bases")
    if not pairs:
        now = datetime.now(UTC)
        return QualifiedSnapshot(generated_at=now, as_of=now, scan_id=0, opportunities=[])

    volumes = fetch_venue_volumes(entry, ex, pairs)
    kept = [p for p in pairs if volumes.get(p, 0.0) >= settings.min_volume_usd]
    progress.log(
        f"Venue {entry.id}: ticker prefilter {len(kept)} of {len(pairs)} bases "
        f"≥ ${settings.min_volume_usd / 1e6:.2f}M (venue volume; not CMC)"
    )
    until = datetime.now(UTC)
    day_since = until - timedelta(days=40)
    five_since = until - timedelta(hours=3)
    candidates: list[OpportunityRow] = []
    for pair in kept:
        try:
            daily = _fetch_ohlcv_points(entry, ex, pair, "1d", day_since, until)
            if len(daily) < 2:
                continue
            gain = (daily[-1].close / daily[0].close) - 1.0 if daily[0].close else 0.0
            if settings.min_gain_pct > 0 and gain < settings.min_gain_pct:
                continue
            five = _fetch_ohlcv_points(entry, ex, pair, "5m", five_since, until)
            if len(five) < 5:
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
                for b in five
            ]
            uni = uniformity_score(bars)
            if uni < settings.min_uniformity:
                continue
            vol = float(volumes.get(pair, 0.0))
            candidates.append(
                OpportunityRow(
                    rank=0,
                    pair=pair,
                    uniformity=uni,
                    gain_pct=gain,
                    volume_score=vol,
                    entry_signal=True,
                    sparkline=[round(b.close, 2) for b in five[-12:]],
                )
            )
        except Exception as exc:
            progress.log(f"Venue {entry.id}: {pair} skipped ({exc})", level="warn")
            continue
        # Soft pause so we do not slam the venue.
        time.sleep(0.05)

    candidates.sort(key=lambda o: (o.uniformity, o.gain_pct), reverse=True)
    ranked = [
        OpportunityRow(rank=i + 1, **{k: v for k, v in o.model_dump().items() if k != "rank"})
        for i, o in enumerate(candidates)
    ]
    progress.log(f"Venue {entry.id}: qualified {len(ranked)} pairs")
    now = datetime.now(UTC)
    return QualifiedSnapshot(
        generated_at=now,
        as_of=now,
        scan_id=0,
        degraded=False,
        opportunities=ranked,
    )
