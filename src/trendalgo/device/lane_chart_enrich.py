"""Post-filter Alpaca 1h enrich for TradFi/FX board charts + HV/DD/Vol Δ."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from trendalgo.backtest.load_days import SCAN_LOOKBACK_HOURS, trim_closes
from trendalgo.device.lane_chart_fetch import fetch_lane_1h_bars
from trendalgo.device.lts_scan_model import normalize_coin
from trendalgo.device.scan_identity import coin_exchange_id
from trendalgo.lts_vendor.chart_closes import closes_from_bars, gain_pct_from_closes
from trendalgo.lts_vendor.utils.scan_artifacts import risk_context_from_hourly_closes
from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner.volume_acceleration import apply_volume_acceleration

_HOUR_LOOKBACK_DAYS = 31


def enrich_lane_coins_1h(
    root: Path,
    coins: list[dict[str, Any]],
    *,
    lane: str,
    progress: Any | None = None,
) -> list[dict[str, Any]]:
    """Stamp hourly closes, risk_context, Vol Δ%, and chart OHLC bars on lane coins."""
    if not coins:
        return coins
    eid = (lane or "").strip().lower()
    until = datetime.now(tz=UTC)
    since = until - timedelta(days=_HOUR_LOOKBACK_DAYS)
    pairs = [str(c.get("pair") or "").strip().upper() for c in coins if c.get("pair")]
    if progress is not None:
        progress.phase("Enrich · 1h charts + HV/DD/Vol Δ", total=len(pairs), unit="pairs")
        label = "Alpaca" if eid == "tradfi" else "FX 1h"
        progress.log(f"{label} enrich for {len(pairs)} {eid} pairs")
    bars_by_pair = fetch_lane_1h_bars(root, pairs, since, until, lane=eid, progress=progress)
    out: list[dict[str, Any]] = []
    for coin in coins:
        row = dict(coin)
        pair = str(row.get("pair") or "").strip().upper()
        _stamp_coin(row, bars_by_pair.get(pair) or [], exchange_id=eid)
        out.append(normalize_coin(row))
    return out


def frame_from_lane_ohlc(coin: dict[str, Any]) -> pd.DataFrame:
    """Real OHLC DataFrame from enrich-stamped bars (true high/low wicks)."""
    raw = coin.get("chart_ohlc_1h")
    if not isinstance(raw, list) or len(raw) < 2:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            rows.append(
                {
                    "timestamp": pd.Timestamp(int(item["t"]), unit="s", tz="UTC"),
                    "open": float(item["o"]),
                    "high": float(item["h"]),
                    "low": float(item["l"]),
                    "close": float(item["c"]),
                    "volume": float(item.get("v") or 0),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    if len(rows) < 2:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("timestamp").sort_index()


def _stamp_coin(coin: dict[str, Any], bars: list[OhlcvPoint], *, exchange_id: str) -> None:
    h_win = trim_closes(closes_from_bars(bars, cap=SCAN_LOOKBACK_HOURS), hours=SCAN_LOOKBACK_HOURS)
    if h_win:
        coin["closes_1h"] = h_win
        coin["chart_closes_1h"] = list(h_win)
    else:
        coin.pop("closes_1h", None)
        coin["chart_closes_1h"] = []
    if bars:
        coin["chart_ohlc_1h"] = [
            {
                "t": int(p.time),
                "o": float(p.open),
                "h": float(p.high),
                "l": float(p.low),
                "c": float(p.close),
                "v": float(p.volume),
            }
            for p in bars[-SCAN_LOOKBACK_HOURS:]
        ]
    else:
        coin.pop("chart_ohlc_1h", None)
    gains = dict(coin.get("gains") or {})
    g7 = gain_pct_from_closes(h_win[-168:]) if len(h_win) >= 168 else gain_pct_from_closes(h_win)
    g30 = gain_pct_from_closes(h_win) if len(h_win) >= 2 else None
    if g7 is not None:
        gains["7d"] = round(g7, 6)
    if g30 is not None:
        gains["30d"] = round(g30, 6)
    if gains:
        coin["gains"] = gains
    if h_win:
        rc = risk_context_from_hourly_closes(h_win)
        if rc:
            coin["risk_context"] = rc
            if rc.get("hv_7d_annualized_pct") is not None:
                coin["hv_7d_pct"] = rc["hv_7d_annualized_pct"]
            if rc.get("max_drawdown_30d_pct") is not None:
                coin["max_drawdown_pct"] = rc["max_drawdown_30d_pct"]
    if exchange_id == "forex":
        _stamp_forex_volume(coin, bars)
        coin["ohlcv_source"] = "algospecial" if bars else "none"
    else:
        apply_volume_acceleration(coin, bars)
        if bars:
            recent = bars[-24:] if len(bars) >= 24 else bars
            tick_vol = float(sum(float(p.volume) for p in recent))
            if tick_vol > 0 and float(coin.get("volume_24h") or 0) <= 0:
                coin["volume_24h"] = tick_vol
            coin["ohlcv_source"] = "alpaca"
        else:
            coin["ohlcv_source"] = "alpaca"
    coin["exchange_id"] = exchange_id or coin_exchange_id(coin)


def _stamp_forex_volume(coin: dict[str, Any], bars: list[OhlcvPoint]) -> None:
    """FX free feeds often ship 0 tick volume — fall back to true-range activity."""
    if not bars:
        apply_volume_acceleration(coin, bars)
        return
    vols = [float(p.volume) for p in bars]
    if any(v > 0 for v in vols[-48:]):
        apply_volume_acceleration(coin, bars)
        recent = bars[-24:] if len(bars) >= 24 else bars
        coin["volume_24h"] = float(sum(float(p.volume) for p in recent))
        coin["volume_unit"] = "ticks"
        return
    # Relative activity proxy (scaled true range) so Vol / Vol Δ% are comparable across pairs.
    activity = _true_range_activity(bars)
    scaled = [a * 100_000.0 for a in activity]
    from trendalgo.scanner.volume_acceleration import VOLUME_KEYS, volume_acceleration_stats

    for key in VOLUME_KEYS:
        coin.pop(key, None)
    stats = volume_acceleration_stats(scaled)
    if stats is not None:
        coin.update(stats)
    recent = scaled[-24:] if len(scaled) >= 24 else scaled
    coin["volume_24h"] = float(sum(recent))
    coin["volume_unit"] = "range"


def _true_range_activity(bars: list[OhlcvPoint]) -> list[float]:
    out: list[float] = []
    prev_c: float | None = None
    for p in bars:
        high, low, close = float(p.high), float(p.low), float(p.close)
        tr = max(0.0, high - low)
        if prev_c is not None:
            tr = max(tr, abs(high - prev_c), abs(low - prev_c))
        out.append(tr)
        prev_c = close
    return out
