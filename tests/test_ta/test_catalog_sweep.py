"""TA catalog and sweep tests."""

from trendalgo.ta.catalog import TA_FUNCTION_NAMES, ta_function_count
from trendalgo.ta.sweep import run_ta_sweep


def test_ta_catalog_has_full_list() -> None:
    assert ta_function_count() >= 130
    assert "MACD" in TA_FUNCTION_NAMES
    assert "RSI" in TA_FUNCTION_NAMES
    assert "CDLENGULFING" in TA_FUNCTION_NAMES


def test_ta_sweep_ranks_btc_kraken_1h() -> None:
    result = run_ta_sweep(pair="BTC/USD", exchange_id="kraken", timeframe="1h")
    assert result["pair"] == "BTC/USD"
    assert result["timeframe"] == "1h"
    assert result["sweep_count"] >= 1
    assert result["best"] is not None
    assert "indicator" in result["best"]
