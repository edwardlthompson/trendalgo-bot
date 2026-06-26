"""Dry-run portfolio fixtures per exchange (S14)."""

from __future__ import annotations

from trendalgo.portfolio.db import HoldingRow

DRY_RUN_HOLDINGS: dict[str, list[HoldingRow]] = {
    "kraken": [
        HoldingRow(asset="USD", quantity=1000.0, price_usd=1.0, value_usd=1000.0, cost_basis_usd=1000.0),
        HoldingRow(asset="BTC", quantity=0.01, price_usd=50000.0, value_usd=500.0, cost_basis_usd=450.0),
    ],
    "binanceus": [
        HoldingRow(asset="ETH", quantity=0.5, price_usd=3000.0, value_usd=1500.0, cost_basis_usd=1400.0),
        HoldingRow(asset="USD", quantity=200.0, price_usd=1.0, value_usd=200.0, cost_basis_usd=200.0),
    ],
    "coinbaseadvanced": [
        HoldingRow(asset="BTC", quantity=0.005, price_usd=50000.0, value_usd=250.0, cost_basis_usd=240.0),
        HoldingRow(asset="USD", quantity=350.0, price_usd=1.0, value_usd=350.0, cost_basis_usd=350.0),
    ],
    "gemini": [
        HoldingRow(asset="ETH", quantity=0.2, price_usd=3000.0, value_usd=600.0, cost_basis_usd=580.0),
        HoldingRow(asset="USD", quantity=150.0, price_usd=1.0, value_usd=150.0, cost_basis_usd=150.0),
    ],
    "bitstamp": [
        HoldingRow(asset="BTC", quantity=0.003, price_usd=50000.0, value_usd=150.0, cost_basis_usd=145.0),
        HoldingRow(asset="USD", quantity=280.0, price_usd=1.0, value_usd=280.0, cost_basis_usd=280.0),
    ],
    "cryptocom": [
        HoldingRow(asset="SOL", quantity=2.0, price_usd=150.0, value_usd=300.0, cost_basis_usd=290.0),
        HoldingRow(asset="USD", quantity=220.0, price_usd=1.0, value_usd=220.0, cost_basis_usd=220.0),
    ],
    "binance": [
        HoldingRow(asset="USDT", quantity=500.0, price_usd=1.0, value_usd=500.0, cost_basis_usd=500.0),
        HoldingRow(asset="BTC", quantity=0.008, price_usd=50000.0, value_usd=400.0, cost_basis_usd=380.0),
    ],
    "bybit": [
        HoldingRow(asset="USDT", quantity=300.0, price_usd=1.0, value_usd=300.0, cost_basis_usd=300.0),
        HoldingRow(asset="SOL", quantity=5.0, price_usd=150.0, value_usd=750.0, cost_basis_usd=700.0),
    ],
    "okx": [
        HoldingRow(asset="USDT", quantity=400.0, price_usd=1.0, value_usd=400.0, cost_basis_usd=400.0),
        HoldingRow(asset="ETH", quantity=0.1, price_usd=3000.0, value_usd=300.0, cost_basis_usd=290.0),
    ],
}
