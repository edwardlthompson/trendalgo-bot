"""Env-backed settings object for vendored ``runner_params_from_settings``."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace


def _data_dir() -> Path:
    return Path(os.environ.get("TRENDALGO_DATA_DIR", "data")).resolve()


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str, default: list[str] | None) -> list[str]:
    """Parse comma-separated env. Missing → default; explicit empty → []."""
    raw = os.environ.get(name)
    if raw is None:
        return list(default or [])
    if not str(raw).strip():
        return []
    return [p.strip() for p in str(raw).split(",") if p.strip()]


def _build() -> SimpleNamespace:
    # Defaults match upstream LTS config.settings (empty indicators → full registry).
    base = _data_dir()
    return SimpleNamespace(
        coingecko_calls_per_minute=_int("COINGECKO_CALLS_PER_MINUTE", 30),
        cmc_api_key=os.environ.get("CMC_API_KEY", ""),
        cmc_calls_per_minute=_int("CMC_CALLS_PER_MINUTE", 30),
        polygon_calls_per_minute=_int("POLYGON_CALLS_PER_MINUTE", 5),
        ohlcv_min_1h_bars_per_day=_int("OHLCV_MIN_1H_BARS_PER_DAY", 20),
        ohlcv_min_1h_bars_slack=_int("OHLCV_MIN_1H_BARS_SLACK", 2),
        ohlcv_min_1h_bars_floor=_int("OHLCV_MIN_1H_BARS_FLOOR", 48),
        ohlcv_min_1d_bars_slack=_int("OHLCV_MIN_1D_BARS_SLACK", 2),
        ohlcv_min_1d_bars_floor=_int("OHLCV_MIN_1D_BARS_FLOOR", 14),
        backtest_exchanges=_csv("BACKTEST_EXCHANGES", ["kraken"]),
        backtest_require_target_exchange=_bool("BACKTEST_REQUIRE_TARGET_EXCHANGE", False),
        backtest_max_coins_per_run=_int("BACKTEST_MAX_COINS_PER_RUN", 0),
        base_dir=base,
        backtest_checkpoint_file=base / "lts_backtest_checkpoint.json",
        backtest_telemetry_file=base / "lts_backtest_telemetry.jsonl",
        backtest_timeframes=_csv("BACKTEST_TIMEFRAMES", ["1h", "4h"]),
        backtest_indicators=_csv("BACKTEST_INDICATORS", []),
        backtest_trailing_stop_min=_int("BACKTEST_TRAILING_STOP_MIN", 2),
        backtest_trailing_stop_max=_int("BACKTEST_TRAILING_STOP_MAX", 20),
        backtest_trailing_stop_step=_int("BACKTEST_TRAILING_STOP_STEP", 2),
        backtest_failure_samples_limit=_int("BACKTEST_FAILURE_SAMPLES_LIMIT", 200),
        backtest_enabled=_bool("BACKTEST_ENABLED", True),
        backtest_resume_enabled=_bool("BACKTEST_RESUME_ENABLED", False),
        backtest_parallel_workers=_int("BACKTEST_PARALLEL_WORKERS", 8),
        backtest_max_param_combos=_int("BACKTEST_MAX_PARAM_COMBOS", 100),
        db_paths={"scanner": str(base / "lts_price_cache.db")},
        cache_price_hours=_int("CACHE_PRICE_HOURS", 12),
        backtest_starting_capital=_float("BACKTEST_STARTING_CAPITAL", 1000.0),
        backtest_fee_bps_round_trip=_float("BACKTEST_FEE_BPS_ROUND_TRIP", 52.0),
        backtest_per_coin_timeout_seconds=_int("BACKTEST_PER_COIN_TIMEOUT_SECONDS", 1800),
    )


settings = _build()
