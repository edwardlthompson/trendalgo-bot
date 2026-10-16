"""Device scans pin $1000 stake and pass fees through LTS rows."""

from __future__ import annotations

from trendalgo.device.scan_stake import DEVICE_SCAN_STAKE_USD
from trendalgo.device.scanner_all_ta_prune import fee_for_exchange, fleet_row_to_lts


def test_device_scan_stake_is_1000() -> None:
    assert DEVICE_SCAN_STAKE_USD == 1000.0


def test_fleet_row_includes_fees() -> None:
    row = fleet_row_to_lts(
        {
            "strategy_id": "RSI",
            "timeframe": "4h",
            "net_profit": 40.0,
            "gross_profit": 50.0,
            "fees_paid": 10.0,
            "fee_taker_pct": 0.0026,
            "trades": 2,
            "win_rate": 0.5,
            "tsl_hits": 0,
            "trailing_stop_pct": 0.02,
            "params": {"timeperiod": 14},
        },
        symbol="BTC",
        stake_usd=DEVICE_SCAN_STAKE_USD,
    )
    assert row["fees_paid"] == 10.0
    assert row["stake_usd"] == 1000.0
    assert abs(row["net_pct"] - 4.0) < 1e-9


def test_fee_for_exchange_fallback() -> None:
    fee = fee_for_exchange("no-such-venue", 52.0)
    assert fee.exchange_id == "no-such-venue"
    assert abs(fee.taker_pct - 0.0026) < 1e-9
