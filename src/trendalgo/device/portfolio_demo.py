"""Top-20 demo portfolio when no real portfolio.db exists."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from trendalgo.portfolio.db import HoldingRow, PortfolioStore

# Approximate mid-2026-style prices for a varied Top-20 demo (not live quotes).
_TOP20: tuple[tuple[str, float, float], ...] = (
    ("BTC", 0.12, 68_000.0),
    ("ETH", 2.5, 3_400.0),
    ("USDT", 4_000.0, 1.0),
    ("BNB", 8.0, 580.0),
    ("SOL", 45.0, 145.0),
    ("XRP", 3_500.0, 0.62),
    ("USDC", 2_500.0, 1.0),
    ("ADA", 4_000.0, 0.45),
    ("AVAX", 80.0, 35.0),
    ("DOGE", 12_000.0, 0.12),
    ("DOT", 200.0, 7.2),
    ("LINK", 150.0, 14.5),
    ("MATIC", 2_000.0, 0.55),
    ("LTC", 25.0, 85.0),
    ("BCH", 8.0, 420.0),
    ("UNI", 120.0, 9.5),
    ("ATOM", 90.0, 8.8),
    ("XLM", 8_000.0, 0.11),
    ("NEAR", 180.0, 5.5),
    ("APT", 100.0, 8.2),
)


def seed_demo_portfolio(path: Path) -> Path:
    """Create a demo portfolio.db with Top-20 holdings and a 30-day equity curve."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        path.unlink()
    store = PortfolioStore(path, create=True)
    account_id = store.get_or_create_account("demo", "Top 20")
    holdings: list[HoldingRow] = []
    total = 0.0
    for i, (asset, qty, price) in enumerate(_TOP20):
        # Vary size so the allocation bar is not uniform.
        scale = 1.0 + (i % 5) * 0.15
        q = qty * scale
        value = q * price
        cost = value * (0.85 + (i % 7) * 0.03)
        holdings.append(HoldingRow(asset, q, price, value, cost_basis_usd=cost))
        total += value
    now = datetime.now(tz=UTC)
    store.insert_snapshot_at(
        account_id,
        total,
        holdings,
        captured_at=now.isoformat(),
        source="demo",
    )
    for day in range(30, -1, -1):
        when = now - timedelta(days=day)
        # Mild upward drift with a mid-window dip for chart interest.
        wave = 1.0 + (30 - day) * 0.004 - (0.03 if 10 <= day <= 14 else 0.0)
        day_total = total * wave
        pnl = day_total - total if day == 0 else day_total * 0.002
        store.upsert_daily_aggregate(
            account_id,
            date=when.date().isoformat(),
            total_usd=day_total,
            daily_pnl_usd=pnl,
            realized_pnl_usd=0.0,
            unrealized_pnl_usd=pnl,
        )
    return path


def is_demo_source(source: str) -> bool:
    return str(source or "").strip().lower() == "demo"
