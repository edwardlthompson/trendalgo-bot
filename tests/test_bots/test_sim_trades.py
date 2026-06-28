from trendalgo.bots.sim_trades import simulated_trades_for_bot
from trendalgo.ta.cache import reset_all_ta_caches


def _ohlcv_from_chart(chart: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for i, point in enumerate(chart):
        price = float(point["value"])
        prev = float(chart[i - 1]["value"]) if i > 0 else price
        rows.append(
            {
                "time": int(point["time"]),
                "open": prev,
                "high": max(prev, price),
                "low": min(prev, price),
                "close": price,
                "volume": 1.0,
            }
        )
    return rows


def test_simulated_trades_start_with_buy() -> None:
    reset_all_ta_caches()
    bot = {
        "id": 1,
        "pair": "BTC/USD",
        "strategy_id": "RSI",
        "equity_usd": 1000.0,
        "timeframe": "60",
        "ta_params": {"timeperiod": 14},
    }
    chart = []
    price = 50_000.0
    for i in range(40):
        wave = (i % 7) * 120
        chart.append({"time": 1_700_000_000 + i * 3600, "value": price + wave})
    ohlcv = _ohlcv_from_chart(chart)
    trades = simulated_trades_for_bot(bot, ohlcv, chart=chart)
    if trades:
        assert trades[0]["side"] == "buy"
        for idx, trade in enumerate(trades):
            if trade["side"] == "sell":
                assert idx > 0
                assert trades[idx - 1]["side"] == "buy"


def test_simulated_trades_real_ohlcv_meta() -> None:
    reset_all_ta_caches()
    bot = {
        "id": 1,
        "pair": "BTC/USD",
        "strategy_id": "RSI",
        "equity_usd": 500.0,
        "timeframe": "60",
        "ta_params": {"timeperiod": 14},
    }
    ohlcv = []
    price = 40_000.0
    for i in range(50):
        p = price + i * 10
        ohlcv.append(
            {
                "time": 1_700_000_000 + i * 3600,
                "open": p - 5,
                "high": p + 15,
                "low": p - 15,
                "close": p,
                "volume": 2.0,
            }
        )
    trades, meta = simulated_trades_for_bot(bot, ohlcv, return_meta=True)
    assert meta.hit in {"miss", "exact", "incremental"}
    assert isinstance(trades, list)
