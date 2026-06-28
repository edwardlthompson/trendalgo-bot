"""Stress-test portfolio: random top-100 holdings across all exchanges."""

from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.exchanges.registry import list_portfolio_exchanges
from trendalgo.market.top100 import Top100Asset, fetch_top100_universe
from trendalgo.portfolio.db import HoldingRow, PortfolioStore

_STABLE = frozenset({"USD", "USDT", "USDC", "DAI", "USD0"})


def stress_portfolio_enabled() -> bool:
    return os.environ.get("TRENDALGO_STRESS_PORTFOLIO", "").lower() in {"1", "true", "yes"}


def _cache_path() -> Path:
    root = Path(os.environ.get("TRENDALGO_DATA_DIR", "data"))
    return root / "stress_portfolio.json"


@dataclass
class _CachedStress:
    seed: int
    generated_at: str
    source: str
    asset_count: int
    exchanges: dict[str, list[dict[str, float | str]]]


def _rows_to_holdings(rows: list[dict[str, float | str]]) -> list[HoldingRow]:
    return [
        HoldingRow(
            asset=str(r["asset"]),
            quantity=float(r["quantity"]),
            price_usd=float(r["price_usd"]),
            value_usd=float(r["value_usd"]),
            cost_basis_usd=float(r["cost_basis_usd"]),
        )
        for r in rows
    ]


def _holdings_to_rows(holdings: list[HoldingRow]) -> list[dict[str, float | str]]:
    return [asdict(h) for h in holdings]


def _quote_asset(exchange_id: str) -> str:
    return "USDT" if exchange_id in {"binance", "bybit", "okx"} else "USD"


def generate_stress_holdings(
    universe: list[Top100Asset],
    exchange_ids: list[str],
    *,
    seed: int = 42,
    assets_min: int = 12,
    assets_max: int = 22,
) -> dict[str, list[HoldingRow]]:
    """Assign random top-100 positions to each exchange with live prices."""
    rng = random.Random(seed)
    tradable = [a for a in universe if a.symbol not in _STABLE and a.price_usd > 0]
    out: dict[str, list[HoldingRow]] = {}
    for exchange_id in exchange_ids:
        pick_count = rng.randint(assets_min, min(assets_max, len(tradable)))
        picked = rng.sample(tradable, pick_count)
        quote = _quote_asset(exchange_id)
        cash = round(rng.uniform(800, 12_000), 2)
        budget = rng.uniform(35_000, 180_000)
        holdings: list[HoldingRow] = [
            HoldingRow(quote, cash, 1.0, cash, cash),
        ]
        weights = [rng.uniform(0.3, 1.0) / (a.market_cap_rank or 50) ** 0.55 for a in picked]
        weight_sum = sum(weights) or 1.0
        for asset, weight in zip(picked, weights, strict=True):
            value = round(budget * (weight / weight_sum), 2)
            if value < 25:
                continue
            qty = value / asset.price_usd
            cost = round(value * rng.uniform(0.6, 1.2), 2)
            holdings.append(
                HoldingRow(
                    asset=asset.symbol,
                    quantity=round(qty, 8),
                    price_usd=round(asset.price_usd, 8 if asset.price_usd < 1 else 2),
                    value_usd=value,
                    cost_basis_usd=cost,
                )
            )
        out[exchange_id] = holdings
    return out


def load_or_build_stress_cache(
    *, seed: int = 42, refresh: bool = False
) -> dict[str, list[HoldingRow]]:
    path = _cache_path()
    if not refresh and path.is_file():
        raw = json.loads(path.read_text(encoding="utf-8"))
        cached = _CachedStress(**raw)
        return {ex: _rows_to_holdings(rows) for ex, rows in cached.exchanges.items()}
    universe = fetch_top100_universe()
    exchange_ids = [e.id for e in list_portfolio_exchanges()]
    holdings = generate_stress_holdings(universe, exchange_ids, seed=seed)
    payload = _CachedStress(
        seed=seed,
        generated_at=datetime.now(UTC).isoformat(),
        source="coingecko-top100",
        asset_count=len(universe),
        exchanges={ex: _holdings_to_rows(rows) for ex, rows in holdings.items()},
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(payload), indent=2), encoding="utf-8")
    return holdings


def stress_holdings_for_exchange(exchange_id: str) -> list[HoldingRow] | None:
    if not stress_portfolio_enabled():
        return None
    cached = load_or_build_stress_cache()
    return cached.get(exchange_id)


def apply_stress_portfolio(
    store: PortfolioStore,
    *,
    seed: int = 42,
    refresh_prices: bool = False,
) -> dict[str, Any]:
    """Write stress snapshots for every portfolio-enabled exchange."""
    holdings_by_exchange = load_or_build_stress_cache(seed=seed, refresh=refresh_prices)
    summaries: list[dict[str, Any]] = []
    total_positions = 0
    for exchange_id, holdings in holdings_by_exchange.items():
        account_id = store.get_or_create_account(exchange_id, "default")
        store.set_account_meta(account_id, "spot")
        total = round(sum(h.value_usd for h in holdings), 2)
        store.insert_snapshot(
            account_id,
            total,
            holdings,
            source=f"stress-{exchange_id}",
        )
        total_positions += len(holdings)
        summaries.append(
            {
                "exchange": exchange_id,
                "account_id": account_id,
                "holdings": len(holdings),
                "total_usd": total,
            }
        )
    aggregated = sum(s["total_usd"] for s in summaries)
    unique_assets = len(
        {h.asset for rows in holdings_by_exchange.values() for h in rows if h.asset not in _STABLE}
    )
    return {
        "mode": "stress",
        "source": "coingecko-top100",
        "exchange_count": len(summaries),
        "total_positions": total_positions,
        "unique_assets": unique_assets,
        "aggregated_usd": round(aggregated, 2),
        "accounts": summaries,
    }
