"""Lane board purity: crypto never paints on Forex (and inverse)."""

from __future__ import annotations

from trendalgo.device.lane_board_filter import filter_lane_coins
from trendalgo.device.scan_progress import progress_file_name


def test_forex_desk_drops_crypto_pairs() -> None:
    rows = [
        {"pair": "EUR/USD", "symbol": "EUR", "exchange_id": "forex"},
        {"pair": "BTC/USD", "symbol": "BTC", "exchange_id": "kraken"},
        {"pair": "PEPE/USD", "symbol": "PEPE", "exchange_id": "kraken"},
    ]
    out = filter_lane_coins(rows, "forex")
    assert [r["pair"] for r in out] == ["EUR/USD"]


def test_crypto_desk_drops_forex_and_tradfi_stamps() -> None:
    rows = [
        {"pair": "ETH/USD", "symbol": "ETH", "exchange_id": "kraken"},
        {"pair": "EUR/USD", "symbol": "EUR", "exchange_id": "forex"},
        {"pair": "AAPL/USD", "symbol": "AAPL", "exchange_id": "tradfi"},
    ]
    out = filter_lane_coins(rows, "crypto")
    assert [r["pair"] for r in out] == ["ETH/USD"]


def test_tradfi_desk_keeps_tradfi_drops_crypto_fx() -> None:
    rows = [
        {"pair": "AAPL/USD", "symbol": "AAPL", "exchange_id": "tradfi"},
        {"pair": "BTC/USD", "symbol": "BTC", "exchange_id": "kraken"},
        {"pair": "GBP/USD", "symbol": "GBP", "exchange_id": "forex"},
    ]
    out = filter_lane_coins(rows, "tradfi")
    assert [r["pair"] for r in out] == ["AAPL/USD"]


def test_progress_file_name_is_lane_scoped() -> None:
    assert progress_file_name("crypto") == "scan_progress.json"
    assert progress_file_name("forex") == "scan_progress_forex.json"
    assert progress_file_name("tradfi") == "scan_progress_tradfi.json"
