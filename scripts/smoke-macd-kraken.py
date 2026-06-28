"""Smoke: MACD Kraken 1h bot, native backtest, TA catalog sweep."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = os.environ.get("TRENDALGO_SMOKE_API", "http://127.0.0.1:8000/api/v1")


def _post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    try:
        catalog = _get("/research/ta-catalog")
        print(f"TA catalog: {catalog['count']} functions, talib={catalog['talib_available']}")

        bot = _post(
            "/bots",
            {
                "label": "MACD BTC/USD 1h Kraken",
                "strategy_id": "macd-kraken-1h",
                "pair": "BTC/USD",
                "equity_usd": 1000.0,
            },
        )
        print(f"Bot created: id={bot.get('id')}")

        backtest = _post(
            "/backtest",
            {
                "strategy": "macd-kraken-1h",
                "pair": "BTC/USD",
                "timeframe": "1h",
                "timerange": "20240101-20240601",
            },
        )
        engine = backtest.get("result", {}).get("metadata", {}).get("engine")
        pnl = backtest.get("result", {}).get("profit_total")
        print(f"Backtest engine={engine} pnl={pnl}")

        sweep = _post(
            "/research/ta-sweep",
            {"pair": "BTC/USD", "exchange_id": "kraken", "timeframe": "1h"},
        )
        best = sweep.get("best") or {}
        print(f"Best TA: {best.get('indicator')} pnl={best.get('profit_total')}")
        print("Smoke OK")
        return 0
    except urllib.error.URLError as exc:
        print(f"Smoke failed — is API running on {API}? {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
