"""Lazy trade-region overlays for scanner fullscreen charts (pure helpers).

Overlays must use the same OHLCV + stake/fee path as All-TA Results (BacktestDataLoader,
30d lookback), never synthetic spark closes — those invent different signals/trade counts.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.load_days import SCAN_LOOKBACK_DAYS
from trendalgo.backtest.ta_fleet import backtest_one, prepare_signals
from trendalgo.backtest.ta_simulator import simulate_long_with_fees, trade_hold_regions
from trendalgo.device.sauce_names import is_sauce, is_sauce_ta
from trendalgo.device.scan_stake import DEVICE_SCAN_STAKE_USD
from trendalgo.device.scanner_all_ta_prune import fee_for_bps

_BH = "B&H"
_DEFAULT_FEE_BPS = 52.0
_SECRET_SID = "GEN_SECRET_1"


def top_strategy_rows(coin: dict[str, Any], *, limit: int | None = None) -> list[dict[str, Any]]:
    """Secret Sauce + B&H-beaters + Oracle max (for chart radios)."""
    raw = coin.get("backtest_top_strategies")
    strategies = [r for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []
    bh = coin.get("backtest_buy_hold")
    oracle = coin.get("backtest_oracle_max")
    bh_net: float | None = None
    if isinstance(bh, dict):
        try:
            bh_net = float(bh.get("net_pct"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            bh_net = None
    sauces: list[dict[str, Any]] = []
    ranked: list[tuple[float, dict[str, Any]]] = []
    for row in strategies:
        name = str(row.get("indicator") or "").strip()
        if name in {_BH, "Oracle max"}:
            continue
        if name.startswith("Secret Sauce"):
            sauces.append(dict(row))
            continue
        try:
            net = float(row.get("net_pct"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if bh_net is not None and net <= bh_net:
            continue
        ranked.append((net, row))
    ranked.sort(key=lambda item: item[0], reverse=True)
    beaters = [dict(row) for _, row in ranked]
    if limit is not None:
        beaters = beaters[: max(0, int(limit))]
    # Lab before TA when both present (stable radio order).
    sauces.sort(key=lambda r: 0 if str(r.get("indicator") or "").endswith("Lab") else 1)
    out: list[dict[str, Any]] = [*sauces, *beaters]
    if isinstance(oracle, dict):
        out.append(dict(oracle))
    return out


def frame_from_closes(closes: list[float], *, hours_step: int = 1) -> pd.DataFrame:
    """Synthetic OHLCV from spark closes (display-only fallback; not for overlays)."""
    clean = [float(v) for v in closes if isinstance(v, (int, float)) and v == v]
    if len(clean) < 2:
        return pd.DataFrame()
    end = datetime.now(tz=UTC).replace(minute=0, second=0, microsecond=0)
    index = pd.DatetimeIndex(
        [end - timedelta(hours=hours_step * (len(clean) - 1 - i)) for i in range(len(clean))],
        tz="UTC",
    )
    close = pd.Series(clean, index=index, dtype=float)
    open_ = close.shift(1).fillna(close.iloc[0])
    return pd.DataFrame(
        {
            "open": open_,
            "high": close * 1.001,
            "low": close * 0.999,
            "close": close,
            "volume": 1.0,
        },
        index=index,
    )


def resolve_ohlcv_frame(
    coin: dict[str, Any],
    *,
    timeframe: str,
    candles_db: Path | None = None,  # noqa: ARG001 — kept for call-site compat
    closes: list[float] | None = None,
    for_overlay: bool = False,
) -> pd.DataFrame:
    """OHLCV for chart display or overlay replay.

    Overlay / Results parity: load via BacktestDataLoader (same cache + 30d as All-TA).
    Display-only: fall back to spark closes when the loader has no bars.
    """
    tf = _normalize_tf(timeframe)
    if for_overlay or closes is None:
        frame = _load_scan_frame(coin, timeframe=tf)
        if not frame.empty:
            return frame
    if closes is not None:
        return frame_from_closes(closes, hours_step=1 if tf == "1h" else 4)
    spark = _coin_closes(coin)
    if spark:
        return frame_from_closes(spark, hours_step=1 if tf == "1h" else 4)
    return _load_scan_frame(coin, timeframe=tf)


def regions_for_strategy(
    frame: pd.DataFrame,
    row: dict[str, Any],
    *,
    stake_usd: float | None = None,
    fee_bps: float | None = None,
) -> list[dict[str, Any]]:
    """Re-run one strategy with collect_trades on the scan OHLCV frame."""
    if frame.empty or len(frame) < 20:
        return []
    sid = str(row.get("indicator") or row.get("strategy_id") or "")
    if not sid or sid == _BH:
        return []
    if sid == "Oracle max":
        return regions_from_oracle_swings(frame, list(row.get("oracle_swings") or []))
    stake, bps = _stake_and_fee(stake_usd, fee_bps)
    tsl = _tsl_fraction(row)
    params = row.get("params") if isinstance(row.get("params"), dict) else {}
    fee = fee_for_bps(bps)
    try:
        if (
            is_sauce_ta(sid)
            or bool(params.get("ss_coincidence"))
            or bool(row.get("ss_coincidence"))
        ):
            return _regions_sauce_ta(frame, params, stake=stake, fee=fee, tsl=tsl)
        if is_sauce(sid) or sid.upper().startswith("GEN_SECRET"):
            return _regions_sauce_lab(frame, row, params, stake=stake, fee=fee, tsl=tsl)
        trial, _reason = backtest_one(
            frame,
            sid,
            fee,
            stake,
            timeframe=str(row.get("timeframe") or "1h"),
            lookback_seconds=0,
            params=params or None,
            trailing_stop_pct=tsl,
            phase="chart_overlay",
            collect_trades=True,
        )
    except (KeyError, ValueError, TypeError, IndexError):
        return []
    if trial is None:
        return []
    trades = trial.get("trade_list")
    if not isinstance(trades, list):
        return []
    return trade_hold_regions(trades)


def _regions_sauce_ta(
    frame: pd.DataFrame,
    params: dict[str, Any],
    *,
    stake: float,
    fee: Any,
    tsl: float,
) -> list[dict[str, Any]]:
    e_sid = str(params.get("coincidence_entry") or "").strip()
    x_sid = str(params.get("coincidence_exit") or "").strip()
    if not e_sid or not x_sid:
        return []
    e_prep = prepare_signals(frame, e_sid, {})
    x_prep = prepare_signals(frame, x_sid, {})
    if e_prep[0] is None or x_prep[1] is None:
        return []
    stats = simulate_long_with_fees(
        frame,
        np.asarray(e_prep[0], dtype=bool),
        np.asarray(x_prep[1], dtype=bool),
        stake_usd=stake,
        fee=fee,
        trailing_stop_pct=tsl,
        collect_trades=True,
    )
    trades = stats.get("trade_list")
    return trade_hold_regions(trades) if isinstance(trades, list) else []


def _regions_sauce_lab(
    frame: pd.DataFrame,
    row: dict[str, Any],
    params: dict[str, Any],
    *,
    stake: float,
    fee: Any,
    tsl: float,
) -> list[dict[str, Any]]:
    from trendalgo.backtest.secret_sauce_dossier import dossier_from_dict

    eval_params = dict(params)
    dossier = row.get("heartbeat_dossier")
    if isinstance(dossier, dict):
        cooked = dossier_from_dict(dossier)
        if cooked is not None:
            eval_params = {**eval_params, **cooked.eval_params()}
    sid = str(row.get("strategy_id") or eval_params.get("strategy_id") or _SECRET_SID)
    if not sid.upper().startswith("GEN_SECRET"):
        sid = _SECRET_SID
    trial, _reason = backtest_one(
        frame,
        sid,
        fee,
        stake,
        timeframe=str(row.get("timeframe") or "1h"),
        lookback_seconds=0,
        params=eval_params,
        trailing_stop_pct=tsl,
        phase="chart_overlay",
        collect_trades=True,
    )
    if trial is None:
        return []
    trades = trial.get("trade_list")
    return trade_hold_regions(trades) if isinstance(trades, list) else []


def regions_from_oracle_swings(
    frame: pd.DataFrame,
    swings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Map stored oracle swing indexes onto the overlay frame timestamps."""
    if frame.empty or not swings:
        return []
    closes = frame["close"].to_numpy(dtype=float) if "close" in frame.columns else None
    enriched: list[dict[str, Any]] = []
    for trade in swings:
        item = dict(trade)
        try:
            entry_i = int(trade.get("entry_index") or -1)
            exit_i = int(trade.get("exit_index") or -1)
        except (TypeError, ValueError):
            continue
        if entry_i < 0 or exit_i < 0 or entry_i >= len(frame) or exit_i >= len(frame):
            continue
        item["entry_time"] = item.get("entry_time") or _bar_time(frame, entry_i)
        item["exit_time"] = item.get("exit_time") or _bar_time(frame, exit_i)
        if closes is not None:
            item["entry_price"] = float(closes[entry_i])
            item["exit_price"] = float(closes[exit_i])
        item.setdefault("exit_reason", "oracle_swing")
        if item.get("pnl_pct") is None:
            ep = float(item.get("entry_price") or 0.0)
            xp = float(item.get("exit_price") or 0.0)
            if ep:
                item["pnl_pct"] = round(((xp / ep) - 1.0) * 100.0, 4)
        enriched.append(item)
    return trade_hold_regions(enriched)


def _bar_time(frame: pd.DataFrame, index: int) -> str:
    try:
        from trendalgo.backtest.ta_simulator import _bar_time as sim_bar_time

        return str(sim_bar_time(frame, index))
    except Exception:
        ts = frame.index[index]
        return str(getattr(ts, "isoformat", lambda: ts)())


def overlay_summary(
    frame: pd.DataFrame,
    row: dict[str, Any],
) -> dict[str, Any]:
    """Trade count / net for debugging parity with Results."""
    if frame.empty:
        return {"trades": 0, "net_profit": None}
    sid = str(row.get("indicator") or row.get("strategy_id") or "")
    stake, bps = _stake_and_fee(None, None)
    tsl = _tsl_fraction(row)
    params = row.get("params") if isinstance(row.get("params"), dict) else None
    trial, _reason = backtest_one(
        frame,
        sid,
        fee_for_bps(bps),
        stake,
        timeframe=str(row.get("timeframe") or "1h"),
        lookback_seconds=0,
        params=params,
        trailing_stop_pct=tsl,
        phase="chart_overlay",
        collect_trades=True,
    )
    if trial is None:
        return {"trades": 0, "net_profit": None, "reason": _reason}
    return {
        "trades": int(trial.get("trades") or 0),
        "net_profit": trial.get("net_profit"),
        "trailing_stop_pct": trial.get("trailing_stop_pct"),
    }


def _load_scan_frame(coin: dict[str, Any], *, timeframe: str) -> pd.DataFrame:
    """Same loader path as All-TA pass-1 / deepen."""
    try:
        from trendalgo.lts_vendor import install_import_shims

        install_import_shims()
        from trendalgo.lts_vendor.backtesting.data_loader import BacktestDataLoader
        from trendalgo.lts_vendor.backtesting.params import runner_params_from_settings
        from trendalgo.lts_vendor.shims.database_cache import PriceCache
    except Exception:
        return pd.DataFrame()

    symbol = str(coin.get("symbol") or "").strip().upper()
    pair = str(coin.get("pair") or "")
    load_symbol = pair.split("/", 1)[0].strip().upper() if "/" in pair else symbol
    load_symbol = load_symbol or symbol
    if not load_symbol:
        return pd.DataFrame()
    gecko = coin.get("gecko_id")
    gecko_id = str(gecko) if gecko else None
    try:
        rp = runner_params_from_settings()
        loader = BacktestDataLoader(
            cache=PriceCache(Path(rp.scanner_db_path)),
            max_cache_age_hours=rp.cache_price_hours,
            loader_params=rp.loader,
        )
        loaded = loader.load(
            symbol=load_symbol,
            timeframe=timeframe,
            days=SCAN_LOOKBACK_DAYS,
            gecko_id=gecko_id,
        )
    except Exception:
        return pd.DataFrame()
    frame = getattr(loaded, "frame", None)
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame()
    return frame


def _stake_and_fee(
    stake_usd: float | None,
    fee_bps: float | None,
) -> tuple[float, float]:
    """Match All-TA scan stake; fee bps from settings when not passed."""
    stake = float(stake_usd) if stake_usd is not None else DEVICE_SCAN_STAKE_USD
    if fee_bps is not None:
        return stake, float(fee_bps)
    try:
        from trendalgo.lts_vendor.backtesting.params import runner_params_from_settings

        rp = runner_params_from_settings()
        return stake, float(rp.backtest_fee_bps_round_trip)
    except Exception:
        return stake, _DEFAULT_FEE_BPS


def _coin_closes(coin: dict[str, Any]) -> list[float]:
    for key in ("spark_closes_7d", "closes_1h", "chart_closes_1h", "spark_closes_30d"):
        raw = coin.get(key)
        if isinstance(raw, list) and len(raw) >= 2:
            return [float(x) for x in raw if isinstance(x, (int, float))]
    return []


def _normalize_tf(raw: str) -> str:
    text = str(raw or "").strip()
    aliases = {"60": "1h", "240": "4h", "1H": "1h", "4H": "4h"}
    return aliases.get(text, text if text in {"1h", "4h"} else "1h")


def _tsl_fraction(row: dict[str, Any]) -> float:
    """Results rows: percent (0 = signal-only, 1 = 1%). Simulator wants fraction.

    Mirrors ``tsl_display_pct`` inverse: ``< 1`` is already a fraction; ``>= 1`` is percent.
    Never invent a 1% trail when Results stored signal-only (0).
    """
    raw = row.get("trailing_stop_pct")
    if raw is None:
        raw = row.get("trailing_stop_loss_pct")
    if raw is None:
        return 0.0
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if value <= 0.0:
        return 0.0
    if value < 1.0:
        return value
    return value / 100.0


def overlay_net_pct(regions: list[dict[str, Any]]) -> float | None:
    """Sum of per-trade pnl_pct (All-TA restakes full stake each trade)."""
    total = 0.0
    found = False
    for region in regions:
        raw = region.get("pnl_pct")
        if raw is None:
            continue
        try:
            total += float(raw)
            found = True
        except (TypeError, ValueError):
            continue
    return total if found else None
