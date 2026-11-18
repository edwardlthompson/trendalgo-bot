"""DEX-P3a: CEX-proxy / synthetic backtest disclaimer."""

from __future__ import annotations

from trendalgo.backtest.dex_proxy_bt import (
    DEX_PROXY_BT_DISCLAIMER,
    dex_proxy_bt_public_dict,
    run_dex_proxy_buy_hold,
)
from trendalgo.device.dex_bt_disclaimer import dex_backtest_disclaimer


def test_dex_proxy_buy_hold_synthetic() -> None:
    result = run_dex_proxy_buy_hold("base", "ETH/USDC", prefer="synthetic")
    assert result.bar_count >= 1
    assert result.candle_kind == "synthetic"
    assert "Not on-chain fills" in result.disclaimer
    assert result.degraded
    pub = dex_proxy_bt_public_dict(result)
    assert pub["on_chain_fills"] is False


def test_device_disclaimer_string() -> None:
    assert "Not on-chain fills" in dex_backtest_disclaimer()
    assert DEX_PROXY_BT_DISCLAIMER
