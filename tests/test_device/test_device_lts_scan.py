"""LTS row build/save/normalize for the dense scanner table."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from trendalgo.device.lts_scan_model import (
    build_lts_rows,
    cell_closes,
    filter_coins,
    has_backtest_results,
    load_lts_rows,
    normalize_coin,
    save_filters,
    save_lts_rows,
)
from trendalgo.device.scan_model import device_scan_settings
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot


def _snap() -> QualifiedSnapshot:
    return QualifiedSnapshot(
        generated_at=datetime.now(UTC),
        as_of=datetime.now(UTC),
        scan_id=3,
        opportunities=[
            OpportunityRow(
                rank=1,
                pair="BTC/USD",
                uniformity=0.8,
                gain_pct=0.12,
                volume_score=2_000_000,
                entry_signal=True,
                sparkline=[1.0, 1.1, 1.2],
            )
        ],
    )


def test_build_without_enrich_keeps_sparkline(tmp_path: Path) -> None:
    rows = build_lts_rows(_snap(), enrich_charts=False)
    assert rows[0]["symbol"] == "BTC"
    assert rows[0]["chart_closes_1h"] == [1.0, 1.1, 1.2]
    save_lts_rows(tmp_path, rows)
    assert load_lts_rows(tmp_path)[0]["symbol"] == "BTC"


def test_cell_closes_prefers_closes_then_chart_closes() -> None:
    assert cell_closes({"closes_1h": [1.0, 2.0]}, "closes_1h") == [1.0, 2.0]
    assert cell_closes({"chart_closes_1h": [3.0, 4.0]}, "closes_1h") == [3.0, 4.0]
    assert cell_closes({"closes_1d": [5.0, 6.0]}, "chart_closes_1d") == [5.0, 6.0]


def test_normalize_flattens_risk_context() -> None:
    coin = normalize_coin(
        {
            "symbol": "ETH",
            "risk_context": {"hv_7d_annualized_pct": 40.0, "max_drawdown_30d_pct": -12.0},
        }
    )
    assert coin["hv_7d_pct"] == 40.0
    assert coin["max_drawdown_pct"] == -12.0


def test_save_marks_new_symbols(tmp_path: Path) -> None:
    save_lts_rows(tmp_path, [{"symbol": "BTC", "pair": "BTC/USD"}])
    save_lts_rows(
        tmp_path,
        [
            {"symbol": "BTC", "pair": "BTC/USD"},
            {"symbol": "ETH", "pair": "ETH/USD"},
        ],
    )
    loaded = {r["symbol"]: r for r in load_lts_rows(tmp_path)}
    assert loaded["BTC"].get("is_new") is False
    assert loaded["ETH"].get("is_new") is True


def test_filter_coins_by_exchange_and_gains() -> None:
    coins = [
        {
            "symbol": "BTC",
            "listed_on": ["kraken"],
            "gains": {"7d": 40.0, "30d": 50.0},
        },
        {
            "symbol": "AAA",
            "listed_on": ["coinbase"],
            "gains": {"7d": 10.0, "30d": 10.0},
        },
    ]
    only_kraken = filter_coins(coins, exchange="Kraken")
    assert [c["symbol"] for c in only_kraken] == ["BTC"]
    high = filter_coins(coins, min_gain_7d=30.0, min_gain_30d=30.0)
    assert [c["symbol"] for c in high] == ["BTC"]


def test_filter_coins_best_bt_and_bot_vs_bh() -> None:
    coins = [
        {"symbol": "BOT", "bot_best_net_pct": 80.0, "bot_vs_bh_pct": 12.0},
        {"symbol": "HOLD", "bot_best_net_pct": 5.0, "bot_vs_bh_pct": -8.0},
        {"symbol": "FLAT", "bot_best_net_pct": 40.0, "bot_vs_bh_pct": 0.0},
        {"symbol": "MISS", "bot_best_net_pct": None, "bot_vs_bh_pct": None},
    ]
    assert [c["symbol"] for c in filter_coins(coins, min_best_bt=50.0)] == ["BOT"]
    assert [c["symbol"] for c in filter_coins(coins, bot_vs_bh_filter="pos")] == ["BOT"]
    assert [c["symbol"] for c in filter_coins(coins, bot_vs_bh_filter="neg")] == ["HOLD"]


def test_has_backtest_results() -> None:
    assert has_backtest_results({"bot_best_net_pct": 12.0})
    assert has_backtest_results({"backtest_top_strategies": [{"name": "x"}]})
    assert not has_backtest_results({})


def test_filters_override_min_gain_percent(tmp_path: Path) -> None:
    save_filters(tmp_path, {"min_gain_pct": 30, "min_volume_usd": 500_000})
    settings = device_scan_settings(tmp_path)
    assert settings.min_gain_pct == 0.3
    assert settings.min_volume_usd == 500_000


def test_filters_prefer_min_gain_30d(tmp_path: Path) -> None:
    save_filters(tmp_path, {"min_gain_30d": 25, "min_gain_pct": 99})
    settings = device_scan_settings(tmp_path)
    assert settings.min_gain_pct == 0.25


def test_coins_for_backtest_applies_volume_and_gain_floors() -> None:
    from trendalgo.device.lts_scan_model import coins_for_backtest

    coins = [
        {
            "symbol": "HOT",
            "gains": {"7d": 20.0, "30d": 40.0},
            "volume_24h": 2_000_000,
        },
        {
            "symbol": "COLD",
            "gains": {"7d": 1.0, "30d": 40.0},
            "volume_24h": 2_000_000,
        },
        {
            "symbol": "THIN",
            "gains": {"7d": 20.0, "30d": 40.0},
            "volume_24h": 100_000,
        },
    ]
    kept = coins_for_backtest(
        coins,
        {
            "min_gain_7d": 7.0,
            "min_gain_30d": 30.0,
            "min_volume_usd": 1_000_000,
        },
    )
    assert [c["symbol"] for c in kept] == ["HOT"]
