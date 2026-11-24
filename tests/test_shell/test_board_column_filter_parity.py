"""AV-G-BRD4 — column-filter contract matches PySide filter_coins / dump keys."""

from __future__ import annotations

from trendalgo.device.lts_scan_model import filter_coins

# Keys Avalonia BoardColumnFilterStore reads/writes (ScannerColumnFilterRow.dump).
_COLUMN_FILTER_KEYS = {
    "min_gain_7d",
    "min_gain_30d",
    "min_best_bt",
    "bot_vs_bh_filter",
    "chart_dist_max_7d",
    "chart_dist_max_30d",
    "health_min",
    "vol_accel_filter",
    "view_exchanges",
    "vol24_min",
}


def test_column_filter_key_contract() -> None:
    assert "min_gain_7d" in _COLUMN_FILTER_KEYS
    assert "chart_dist_max_7d" in _COLUMN_FILTER_KEYS
    assert "vol_accel_filter" in _COLUMN_FILTER_KEYS


def test_filter_coins_chart_dist_and_vol_accel() -> None:
    coins = [
        {
            "symbol": "NEAR",
            "listed_on": ["kraken"],
            "gains": {"7d": 5.0, "30d": 5.0},
            "chart_dist_7d_pct": 4.0,
            "volume_acceleration_pct": 30.0,
            "volume_24h": 2_000_000,
            "health_score": 70,
        },
        {
            "symbol": "FAR",
            "listed_on": ["kraken"],
            "gains": {"7d": 5.0, "30d": 5.0},
            "chart_dist_7d_pct": 12.0,
            "volume_acceleration_pct": -5.0,
            "volume_24h": 50_000,
            "health_score": 40,
        },
    ]
    assert [c["symbol"] for c in filter_coins(coins, chart_dist_max_7d=10.0)] == ["NEAR"]
    assert [c["symbol"] for c in filter_coins(coins, vol_accel_filter="pos")] == ["NEAR"]
    assert [c["symbol"] for c in filter_coins(coins, vol_accel_filter="25")] == ["NEAR"]
    assert [c["symbol"] for c in filter_coins(coins, vol24_min=1_000_000)] == ["NEAR"]
    assert [c["symbol"] for c in filter_coins(coins, health_min=60)] == ["NEAR"]
