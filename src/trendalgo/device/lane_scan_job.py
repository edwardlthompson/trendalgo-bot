"""TradFi / Forex opportunity scan: filtered universe, ~30d bars, All-TA on survivors."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from trendalgo.brokers.forex_universe import load_forex_universe
from trendalgo.brokers.tradfi_universe import load_tradfi_universe
from trendalgo.device.alpaca_vault import resolve_alpaca_credentials
from trendalgo.device.db import enable_wal
from trendalgo.device.lane_chart_enrich import enrich_lane_coins_1h
from trendalgo.device.lane_scan_filters import (
    abs_gain_pct,
    avg_dollar_volume,
    last_close,
    load_lane_scan_filters,
    realized_range_pct,
)
from trendalgo.device.lts_scan_model import build_lts_rows, load_watchlist, save_lts_rows
from trendalgo.device.scan_eta_filters import merge_scan_meta
from trendalgo.device.scan_identity import row_key
from trendalgo.device.scan_job import _merge_pass1_backtests
from trendalgo.device.scan_lock import try_acquire_scan_lock
from trendalgo.device.scan_model import scan_store_path
from trendalgo.device.scan_progress import ProgressReporter
from trendalgo.market.alpaca_ohlcv import (
    AlpacaOhlcvProvider,
    fetch_alpaca_equity_bars_multi,
    normalize_alpaca_symbol,
)
from trendalgo.market.ohlcv_disk_cache import load_cached_ohlcv, save_cached_ohlcv
from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner.progress import get_scan_progress, set_scan_progress_lane
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore

LaneScanId = Literal["tradfi", "forex"]

_LOOKBACK_DAYS = 40
_GAIN_BARS = 22
_CHUNK = 100


class AlpacaKeysRequiredError(RuntimeError):
    """TradFi/Forex Opportunity scan refused — no Alpaca credentials."""


class AlpacaForexDataDeniedError(RuntimeError):
    """Forex scan refused — Alpaca account lacks Forex rates market-data grant."""


def tradfi_scan_job(root: Path) -> dict[str, Any]:
    return lane_scan_job(root, "tradfi")


def forex_scan_job(root: Path) -> dict[str, Any]:
    return lane_scan_job(root, "forex")


def lane_scan_job(root: Path, lane: LaneScanId) -> dict[str, Any]:
    if resolve_alpaca_credentials() is None:
        raise AlpacaKeysRequiredError(
            "Alpaca paper API keys are required for TradFi and Forex scans."
        )
    lock = try_acquire_scan_lock(root, lane)
    try:
        return _lane_scan_locked(root, lane)
    except AlpacaForexDataDeniedError:
        # Drop any prior synthetic board so the desk stays empty until live rates work.
        if lane == "forex":
            save_lts_rows(root, [], lane="forex")
            _purge_synthetic_fx_cache(root)
        raise
    finally:
        lock.release()


def _lane_scan_locked(root: Path, lane: LaneScanId) -> dict[str, Any]:
    set_scan_progress_lane(lane)
    progress = get_scan_progress(lane)
    label = "TradFi scan" if lane == "tradfi" else "Forex scan"
    progress.begin_job(label)
    reporter = ProgressReporter(root, lane=lane)
    reporter.start()
    timings: dict[str, float] = {}
    t0 = time.perf_counter()
    try:
        filters = load_lane_scan_filters(root, lane)
        wl_pairs = {p.strip().upper() for p in load_watchlist(root, lane=lane) if p.strip()}
        wl_syms = {p.split("/")[0] for p in wl_pairs}
        symbols = (
            list(load_tradfi_universe(root=root))
            if lane == "tradfi"
            else list(load_forex_universe())
        )
        seen_sym = {s.strip().upper() for s in symbols}
        for wl_item in sorted(wl_syms if lane == "tradfi" else wl_pairs):
            if wl_item and wl_item not in seen_sym:
                symbols.append(wl_item)
                seen_sym.add(wl_item)
        progress.log(f"Universe: {len(symbols)} {lane} symbols")
        progress.phase(f"{label} · bars", total=len(symbols), unit="pairs")
        until = datetime.now(tz=UTC)
        since = until - timedelta(days=_LOOKBACK_DAYS)
        exchange_id = "tradfi" if lane == "tradfi" else "forex"

        t_bars = time.perf_counter()
        bars_by_pair = (
            _fetch_tradfi_bars(root, symbols, since, until, progress=progress)
            if lane == "tradfi"
            else _fetch_forex_bars(root, symbols, since, until, progress=progress)
        )
        timings["bars_s"] = round(time.perf_counter() - t_bars, 3)

        scored: list[tuple[str, list[OhlcvPoint], float, float, float]] = []
        skipped = 0
        for pair, points in bars_by_pair.items():
            if len(points) < 2:
                skipped += 1
                continue
            is_watched = pair.upper() in wl_pairs or pair.split("/")[0].upper() in wl_syms
            adv = avg_dollar_volume(points) if lane == "tradfi" else 0.0
            price = last_close(points)
            gain = _gain_fraction(points)
            if lane == "tradfi" and not is_watched:
                if filters.min_adv_usd > 0 and adv < filters.min_adv_usd:
                    skipped += 1
                    continue
                if filters.min_price > 0 and price < filters.min_price:
                    skipped += 1
                    continue
                move = abs_gain_pct(points)
                if filters.min_abs_gain_pct > 0 and move < filters.min_abs_gain_pct:
                    skipped += 1
                    continue
                rng = realized_range_pct(points)
                if filters.min_range_pct > 0 and rng < filters.min_range_pct:
                    skipped += 1
                    continue
                sort_key = abs(gain)
            else:
                sort_key = abs(gain)
            scored.append((pair, points, gain, adv, sort_key))

        scored.sort(key=lambda t: t[4], reverse=True)
        if lane == "tradfi" and filters.top_n > 0:
            kept = scored[: filters.top_n]
            kept_pairs = {t[0].upper() for t in kept}
            for item in scored[filters.top_n :]:
                p_up = item[0].upper()
                if p_up in wl_pairs or p_up.split("/")[0] in wl_syms:
                    if p_up not in kept_pairs:
                        kept.append(item)
                        kept_pairs.add(p_up)
        else:
            kept = scored
        progress.log(
            f"Filters: kept {len(kept)}/{len(symbols)} pairs "
            f"(|move|≥{filters.min_abs_gain_pct}% range≥{filters.min_range_pct}% "
            f"top_n={filters.top_n or 'all'} adv≥{filters.min_adv_usd:,.0f} "
            f"price≥{filters.min_price})"
        )

        rows: list[OpportunityRow] = []
        for idx, (pair, points, gain, adv, _sk) in enumerate(kept, start=1):
            # Full daily series (~40 bars) for 7d vs 30d sparks/gains in normalize_coin.
            spark = [float(p.close) for p in points]
            rows.append(
                OpportunityRow(
                    rank=idx,
                    pair=pair,
                    uniformity=1.0,
                    gain_pct=gain,
                    volume_score=adv if lane == "tradfi" else float(points[-1].volume),
                    entry_signal=gain > 0,
                    sparkline=spark,
                )
            )

        now = datetime.now(tz=UTC)
        snapshot = QualifiedSnapshot(
            generated_at=now,
            as_of=now,
            scan_id=1,
            degraded=skipped > 0,
            opportunities=rows,
        )
        path = scan_store_path(root, lane)
        enable_wal(path)
        scan_id = ScannerStore(path).save_snapshot(snapshot)
        lts = build_lts_rows(snapshot, enrich_charts=False, exchange_id=exchange_id)
        for coin, (_pair, _pts, _g, adv, _sk) in zip(lts, kept, strict=False):
            if lane == "tradfi":
                coin["volume_24h"] = adv
            p_up = str(coin.get("pair") or "").strip().upper()
            if p_up in wl_pairs or p_up.split("/")[0] in wl_syms:
                coin["watch"] = True
        # Crypto-parity board: real 1h wicks + HV / Max DD / Vol Δ from Alpaca hours.
        t_enr = time.perf_counter()
        lts = enrich_lane_coins_1h(root, lts, lane=lane, progress=progress)
        timings["enrich_s"] = round(time.perf_counter() - t_enr, 3)
        save_lts_rows(root, lts, lane=lane)

        bt_meta: dict[str, Any] = {}
        if lts:
            progress.log(f"All-TA pass-1 on {len(lts)} filtered {lane} pairs")
            t_bt = time.perf_counter()
            bt_rows, bt_meta = _merge_pass1_backtests(lts, root)
            timings["backtest_s"] = round(time.perf_counter() - t_bt, 3)
            by_key = {row_key(c): c for c in bt_rows}
            lts = [by_key.get(row_key(c), c) for c in lts]
            save_lts_rows(root, lts, lane=lane)

        timings["total_s"] = round(time.perf_counter() - t0, 3)
        merge_scan_meta(
            root,
            elapsed_s=timings["total_s"],
            funnel={
                "listed_n": len(symbols),
                "after_volume_n": len(scored),
                "after_activity_n": len(scored),
                "qualified_n": len(lts),
                "min_volume_usd": float(filters.min_adv_usd),
                "require_continuous_1h": False,
            },
            lane=lane,
        )
        progress.log(
            f"{label} done: {len(lts)} pairs · skipped={skipped} · scan_id={scan_id}",
            level="success",
        )
        return {
            "pairs": len(lts),
            "skipped": skipped,
            "scan_id": scan_id,
            "lane": lane,
            "degraded": snapshot.degraded,
            "backtest": bt_meta,
            "timings": timings,
            "data_source": "Alpaca paper (keyed)",
            "filters": {
                "min_adv_usd": filters.min_adv_usd,
                "min_price": filters.min_price,
                "min_abs_gain_pct": filters.min_abs_gain_pct,
                "min_range_pct": filters.min_range_pct,
                "top_n": filters.top_n,
            },
            "universe": len(symbols),
        }
    finally:
        progress.end_job()
        reporter.stop()


def _fetch_tradfi_bars(
    root: Path,
    symbols: list[str],
    since: datetime,
    until: datetime,
    *,
    progress: Any,
) -> dict[str, list[OhlcvPoint]]:
    out: dict[str, list[OhlcvPoint]] = {}
    missing: list[str] = []
    for i, raw in enumerate(symbols, start=1):
        sym = normalize_alpaca_symbol(raw)
        pair = f"{sym}/USD"
        cached = load_cached_ohlcv(root, pair, "1d", since, until)
        if cached:
            out[pair] = cached
        else:
            missing.append(sym)
        if i % 50 == 0:
            progress.step(i, total=len(symbols), pair=pair)
    if missing:
        chunks = (len(missing) + _CHUNK - 1) // _CHUNK
        progress.phase("TradFi · multi-bars", total=chunks, unit="chunks")
        progress.log(f"Alpaca multi-bars fetch: {len(missing)} uncached · chunks={chunks} · paced")
        cached_n = len(symbols) - len(missing)

        def _on_chunk(done: int, total: int, sample: str) -> None:
            # Map chunk progress onto symbol totals so the bar keeps moving.
            approx = cached_n + min(len(missing), done * _CHUNK)
            progress.step(min(approx, len(symbols)), total=len(symbols), pair=f"{sample}/USD")
            progress.log(f"Multi-bars chunk {done}/{total} · {sample}")

        try:
            fetched = fetch_alpaca_equity_bars_multi(
                missing, "1d", since, until, chunk_size=_CHUNK, on_chunk=_on_chunk
            )
        except Exception as exc:  # noqa: BLE001
            progress.log(f"Multi-bars failed ({exc}); falling back per-pair", level="warn")
            fetched = {}
            provider = AlpacaOhlcvProvider(allow_synthetic_fallback=False)
            for j, sym in enumerate(missing, start=1):
                pair = f"{sym}/USD"
                progress.step(cached_n + j, total=len(symbols), pair=pair)
                try:
                    points = provider.fetch("alpaca", pair, "1d", since, until)
                    if points:
                        fetched[sym] = points
                except Exception as sym_exc:  # noqa: BLE001
                    progress.log(f"{pair}: skipped ({sym_exc})", level="warn")
        for sym, points in fetched.items():
            pair = f"{sym}/USD"
            if points:
                save_cached_ohlcv(root, pair, "1d", since, until, points)
                out[pair] = points
    progress.step(len(symbols), total=len(symbols), pair="—")
    return out


def _fetch_forex_bars(
    root: Path,
    symbols: list[str],
    since: datetime,
    until: datetime,
    *,
    progress: Any,
) -> dict[str, list[OhlcvPoint]]:
    """Alpaca FX when granted; else AlgoSpecial H1→D1. Never synthetic."""
    from trendalgo.device.forex_bars import fetch_forex_daily_bars

    out = fetch_forex_daily_bars(root, symbols, since, until, progress=progress)
    if not out and symbols:
        raise AlpacaForexDataDeniedError(
            "No Forex bars from Alpaca or AlgoSpecial (and no usable cache). "
            "Check network / AlgoSpecial cool-down, or enable Alpaca Forex data."
        )
    return out


def _purge_synthetic_fx_cache(root: Path) -> None:
    """Delete OHLCV cache files that look like synthetic FX (volume stuck at 1000)."""
    cache = root / "ohlcv_cache"
    if not cache.is_dir():
        return
    for path in cache.glob("*.json"):
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if (
            '"volume": 1000' in raw
            or '"volume":1000' in raw
            or '"volume": 1000.0' in raw
            or '"volume":1000.0' in raw
        ):
            try:
                path.unlink()
            except OSError:
                continue


def _gain_fraction(points: list[OhlcvPoint]) -> float:
    if len(points) < 2:
        return 0.0
    window = points[-_GAIN_BARS:] if len(points) >= _GAIN_BARS else points
    first = window[0].close
    last = window[-1].close
    if first <= 0:
        return 0.0
    return (last / first) - 1.0
