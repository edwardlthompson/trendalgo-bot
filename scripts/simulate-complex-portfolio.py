#!/usr/bin/env python3
"""Seed a complex multi-exchange portfolio from CoinGecko top-100 live prices."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.multi_exchange import aggregate_holdings
from trendalgo.portfolio.stress_fixture import apply_stress_portfolio


def _overview_smoke(api_base: str) -> dict[str, object]:
    with urllib.request.urlopen(f"{api_base}/portfolio/overview", timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Simulate complex top-100 multi-exchange portfolio"
    )
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("TRENDALGO_DATA_DIR", "data/dev"),
        help="Portfolio DB directory",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--refresh", action="store_true", help="Re-fetch CoinGecko prices")
    parser.add_argument(
        "--api",
        default=os.environ.get("TRENDALGO_SMOKE_API", "http://127.0.0.1:8000/api/v1"),
        help="API base for optional smoke (empty to skip)",
    )
    args = parser.parse_args()

    os.environ["TRENDALGO_DATA_DIR"] = args.data_dir
    os.environ["TRENDALGO_STRESS_PORTFOLIO"] = "1"

    store = PortfolioStore(Path(args.data_dir) / "portfolio.db")

    try:
        result = apply_stress_portfolio(store, seed=args.seed, refresh_prices=args.refresh)
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    agg = aggregate_holdings(store)
    print(f"Stress portfolio applied — {result['exchange_count']} exchanges")
    print(
        f"positions={result['total_positions']} unique_assets={result['unique_assets']} "
        f"aggregated=${result['aggregated_usd']:,.2f}"
    )
    print(f"merged_holdings={len(agg['holdings'])} net_worth=${agg['total_usd']:,.2f}")

    if args.api:
        try:
            overview = _overview_smoke(args.api.rstrip("/"))
            print(
                f"API overview OK — holdings={len(overview.get('holdings', []))} "
                f"net_worth=${overview.get('net_worth_usd')} exchanges={overview.get('exchange_count')}"
            )
        except urllib.error.URLError as exc:
            print(f"API smoke skipped (is server running?): {exc}", file=sys.stderr)

    print("Set TRENDALGO_STRESS_PORTFOLIO=1 and restart the API to serve this portfolio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
