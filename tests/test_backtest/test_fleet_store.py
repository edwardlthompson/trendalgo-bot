"""Tests for fleet SQLite store."""

from pathlib import Path

from trendalgo.backtest.fleet_store import FleetStore


def test_fleet_store_pagination_and_group_by(tmp_path: Path) -> None:
    store = FleetStore(tmp_path / "fleet.db")
    rows = [
        {
            "rank": 1,
            "strategy_id": "RSI",
            "timeframe": "60",
            "net_profit": 10.0,
            "gross_profit": 12.0,
            "fees_paid": 2.0,
            "trades": 3,
            "bar_count": 500,
        },
        {
            "rank": 2,
            "strategy_id": "MACD",
            "timeframe": "60",
            "net_profit": 8.0,
            "gross_profit": 10.0,
            "fees_paid": 2.0,
            "trades": 2,
            "bar_count": 500,
        },
        {
            "rank": 3,
            "strategy_id": "RSI",
            "timeframe": "5",
            "net_profit": 15.0,
            "gross_profit": 17.0,
            "fees_paid": 2.0,
            "trades": 4,
            "bar_count": 800,
        },
    ]
    store.save_run("job1", "kraken", "BTC/USD", 1000.0, {"skipped": 0}, rows)
    store.save_run(
        "job2",
        "kraken",
        "ETH/USD",
        500.0,
        {
            "lookback_days": 30,
            "final_top10": [{"strategy_id": "RSI", "net_profit": 15.0, "timeframe": "60"}],
            "buy_and_hold": {"net_profit": 1.0},
        },
        rows,
    )
    listed = store.list_runs(limit=10)
    assert listed["total"] == 2
    assert listed["runs"][0]["job_id"] == "job2"
    assert listed["runs"][0]["best_net_profit"] == 15.0
    saved = store.get_run("job2")
    assert saved is not None
    assert saved["final_top10"][0]["strategy_id"] == "RSI"
    latest = store.latest(limit=2, offset=0)
    assert latest is not None
    assert latest["total_rankings"] == 3
    assert len(latest["rankings"]) == 2

    grouped = store.latest(group_by="strategy")
    assert grouped is not None
    assert len(grouped["rankings"]) == 2
    assert grouped["rankings"][0]["strategy_id"] == "RSI"
    assert grouped["rankings"][0]["net_profit"] == 15.0

    by_tf = store.latest(group_by="60")
    assert by_tf is not None
    assert all(r["timeframe"] == "60" for r in by_tf["rankings"])
