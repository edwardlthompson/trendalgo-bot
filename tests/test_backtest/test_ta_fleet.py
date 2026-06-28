"""Tests for TA fleet backtest engine."""

from trendalgo.backtest.fleet_runner import FleetPreflightError, validate_fleet_request
from trendalgo.backtest.ta_fleet import merge_rank, run_timeframe_slice
from trendalgo.exchanges.fees import get_fee_schedule
from trendalgo.trading.backtest.walk_forward import fixture_candles


def _ohlcv_dicts(count: int = 200) -> list[dict]:
    candles = fixture_candles(count=count, start=50_000.0, drift=0.0002)
    return [
        {
            "time": c.timestamp_ms // 1000,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in candles
    ]


def test_run_timeframe_slice_mixed_results() -> None:
    ohlcv = _ohlcv_dicts()
    fee = get_fee_schedule("kraken")
    results, skips = run_timeframe_slice(
        ohlcv,
        strategies=("RSI", "MACD", "NOT_A_REAL_STRATEGY_XYZ"),
        fee=fee,
        stake_usd=1000.0,
        timeframe="60",
        lookback_seconds=86_400,
        pair="BTC/USD",
        fetch_tf="1h",
    )
    assert isinstance(results, list)
    assert sum(skips.values()) >= 1


def test_merge_rank_orders_by_net_profit() -> None:
    rows = [
        {"net_profit": 1.0, "strategy_id": "A", "timeframe": "60"},
        {"net_profit": 9.0, "strategy_id": "B", "timeframe": "60"},
    ]
    ranked = merge_rank(rows, top_n=2)
    assert ranked[0]["strategy_id"] == "B"
    assert ranked[0]["rank"] == 1


def test_preflight_rejects_unknown_pair() -> None:
    try:
        validate_fleet_request("kraken", "BOGUS/USD")
        raise AssertionError("expected FleetPreflightError")
    except FleetPreflightError:
        pass


def test_preflight_accepts_btc_usd() -> None:
    eid, pair = validate_fleet_request("kraken", "BTC/USD")
    assert eid == "kraken"
    assert pair == "BTC/USD"
