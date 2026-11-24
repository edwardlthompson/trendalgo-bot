"""Load All-TA / pair-scan OHLCV: OHLCVT 30d 1m when configured, else exclusive bands."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from trendalgo.backtest.heartbeat_tf import comparable_scan_timeframes, is_subhour_tf
from trendalgo.backtest.load_days import SCAN_LOOKBACK_DAYS, days_for_timeframe, trim_ohlcv_frame
from trendalgo.backtest.ohlcv_resample import frames_from_base
from trendalgo.backtest.ta_fleet import MIN_BARS_FLOOR
from trendalgo.device.scan_base_ohlcv_fallback import (  # noqa: F401 — re-export
    fetch_tf_frame,
    load_exclusive_band_frames,
)
from trendalgo.market.kraken_ohlcvt import archive_ready, load_1m_frame, stitch_live_tip
from trendalgo.market.kraken_ohlcvt_meta import mix_allowed, read_archive_coverage, today_utc
from trendalgo.market.ohlcvt_tip_journal import (
    append_tip,
    journal_span_ready,
    load_journal,
    stitch_with_journal,
    write_started,
)
from trendalgo.ta.frame_prep import stamp_scan_frame

KRAKEN_OHLC_BAR_CAP = 720


def load_base_ohlcv_frame(
    *,
    symbol: str,
    pair: str,
    timeframes: tuple[str, ...],
    loader: Any,
    gecko_id: str | None = None,
) -> tuple[pd.DataFrame | None, str, str, float | None]:
    """Legacy 1h loader (30d). Prefer ``load_scan_frames`` for multi-TF scans."""
    del pair, timeframes
    lookback = days_for_timeframe()
    loaded = loader.load(symbol=symbol, timeframe="1h", days=lookback, gecko_id=gecko_id)
    frame = loaded.frame if loaded is not None else None
    source = str(getattr(loaded, "source", "") or "none") if loaded is not None else "none"
    if frame is None or frame.empty:
        return None, "1h", source, None
    return trim_ohlcv_frame(frame, lookback), "1h", source, None


def load_scan_frames(
    *,
    symbol: str,
    pair: str,
    timeframes: tuple[str, ...],
    loader: Any,
    gecko_id: str | None = None,
    prefs_root: Path | None = None,
    ohlcvt_path: str | Path | None = None,
    ohlcvt_auto_tip: bool = True,
    exchange_id: str = "kraken",
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    """Hour band: live 30d 1h. Sub-hour: OHLCVT+journal when configured, else live ~12h.

    TradFi/Forex skip Kraken OHLCVT and load Alpaca bands instead.
    """
    from trendalgo.device.scan_base_ohlcv_alpaca import is_alpaca_lane, load_alpaca_band_frames

    if is_alpaca_lane(exchange_id):
        frames, meta = load_alpaca_band_frames(
            symbol=symbol,
            pair=pair,
            timeframes=timeframes,
            exchange_id=exchange_id,
            prefs_root=prefs_root,
        )
        return {tf: stamp_scan_frame(f) for tf, f in frames.items()}, meta
    path, tip_on, mix = _resolve_ohlcvt(prefs_root, ohlcvt_path, ohlcvt_auto_tip)
    ordered = comparable_scan_timeframes(timeframes, deep_1m=mix)
    sub_only = tuple(tf for tf in ordered if is_subhour_tf(tf))
    hour_only = tuple(tf for tf in ordered if not is_subhour_tf(tf))
    use_tfs = ordered if mix else sub_only
    if use_tfs and archive_ready(path) and path is not None:
        frames, meta = _load_from_ohlcvt(
            symbol=symbol,
            pair=pair,
            timeframes=use_tfs,
            archive_path=path,
            cache_dir=prefs_root,
            stitch_tip=tip_on,
            device_root=prefs_root,
        )
        if frames:
            if mix or not hour_only:
                return frames, meta
            # Sub-hour from archive; hours still exclusive live path if somehow mixed prefs.
            return frames, meta
    frames, meta = load_exclusive_band_frames(
        symbol=symbol, pair=pair, timeframes=timeframes, loader=loader, gecko_id=gecko_id
    )
    return {tf: stamp_scan_frame(f) for tf, f in frames.items()}, meta


def _resolve_ohlcvt(
    prefs_root: Path | None,
    ohlcvt_path: str | Path | None,
    ohlcvt_auto_tip: bool,
) -> tuple[Path | None, bool, bool]:
    from trendalgo.device.scan_bt_prefs import (
        journal_started_date,
        load_scan_bt_prefs,
        resolve_ohlcvt_path,
    )

    prefs = None
    if ohlcvt_path is not None:
        raw = str(ohlcvt_path).strip()
        if prefs_root is not None:
            raw = resolve_ohlcvt_path(prefs_root, raw)
            prefs = load_scan_bt_prefs(prefs_root)
        path = Path(raw) if raw else None
        tip = bool(ohlcvt_auto_tip)
    elif prefs_root is None:
        return None, True, False
    else:
        prefs = load_scan_bt_prefs(prefs_root)
        raw = resolve_ohlcvt_path(prefs_root, str(getattr(prefs, "ohlcvt_path", "") or ""))
        path = Path(raw) if raw else None
        tip = bool(getattr(prefs, "ohlcvt_auto_tip", True))

    cov = read_archive_coverage(path) if path is not None else None
    started = journal_started_date(prefs, root=prefs_root) if prefs is not None else None
    mix = mix_allowed(cov, journal_started=started)
    return path, tip, mix


def _load_from_ohlcvt(
    *,
    symbol: str,
    pair: str,
    timeframes: tuple[str, ...],
    archive_path: Path,
    cache_dir: Path | None,
    stitch_tip: bool,
    device_root: Path | None,
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    frame, stem = load_1m_frame(pair=pair, archive_path=archive_path, cache_dir=cache_dir)
    notes: list[str] = []
    if frame is None or frame.empty:
        return {}, {
            "data_source": "none",
            "cache_age_s": None,
            "notes": [f"OHLCVT miss ({stem})"],
            "base_tf": "1m",
            "n_frames": 0,
            "deep_1m": False,
        }
    sources = [f"1m:ohlcvt:{stem}"]
    root = device_root or cache_dir
    if stitch_tip and root is not None:
        tip = fetch_tf_frame(symbol=symbol, pair=pair, timeframe="1m", days=1)
        if tip is not None and not tip.empty:
            append_tip(root, stem, tip)
            from trendalgo.device.scan_bt_prefs import load_scan_bt_prefs, save_scan_bt_prefs

            prefs = load_scan_bt_prefs(root)
            if not prefs.ohlcvt_journal_started:
                prefs.ohlcvt_journal_started = today_utc().isoformat()
                write_started(root, today_utc())
                save_scan_bt_prefs(root, prefs)
            sources.append("1m:tip")
            # Prefer tip stitch when contiguous; journal bridges larger gaps.
            end_before = frame.index.max()
            stitched = stitch_live_tip(frame, tip)
            if stitched.index.max() > end_before:
                frame = stitched
            else:
                journal = load_journal(root, stem)
                frame = stitch_with_journal(frame, journal)
                if journal is not None and not journal.empty:
                    sources.append("1m:journal")
        else:
            journal = load_journal(root, stem)
            frame = stitch_with_journal(frame, journal)
            if journal is not None and not journal.empty:
                sources.append("1m:journal")
    elif root is not None:
        journal = load_journal(root, stem)
        frame = stitch_with_journal(frame, journal)
        if journal is not None and not journal.empty:
            sources.append("1m:journal")

    frame = trim_ohlcv_frame(frame, SCAN_LOOKBACK_DAYS)
    frames: dict[str, pd.DataFrame] = {}
    for tf, built in frames_from_base(frame, timeframes, base_timeframe="1m").items():
        if len(built) >= MIN_BARS_FLOOR:
            frames[tf] = built
        else:
            notes.append(f"{tf}: {len(built)} bars (<{MIN_BARS_FLOOR})")
    journal = load_journal(root, stem) if root is not None else None
    return frames, {
        "data_source": "+".join(sources),
        "cache_age_s": None,
        "notes": notes,
        "base_tf": "1m",
        "n_frames": len(frames),
        "deep_1m": True,
        "journal_ready": journal_span_ready(journal),
    }


def fetch_1m_frame(
    *,
    symbol: str,
    pair: str,
    days: int = SCAN_LOOKBACK_DAYS,
    exchange_id: str = "kraken",
) -> pd.DataFrame | None:
    return fetch_tf_frame(
        symbol=symbol, pair=pair, timeframe="1m", days=days, exchange_id=exchange_id
    )
