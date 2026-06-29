"""Historical OHLCV download for Kraken spot (dry-run / backtest prep)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def _exchange(exchange_id: str = "kraken") -> Any:
    import ccxt  # lazy — optional at test time

    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True})


def download_ohlcv(
    pair: str = "BTC/USD",
    timeframe: str = "5m",
    limit: int = 500,
    exchange_id: str = "kraken",
) -> list[list[float]]:
    exchange = _exchange(exchange_id)
    rows: list[list[float]] = exchange.fetch_ohlcv(pair, timeframe=timeframe, limit=limit)
    return rows


def save_csv(rows: list[list[float]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["timestamp,open,high,low,close,volume"]
    for row in rows:
        lines.append(",".join(str(x) for x in row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download Kraken OHLCV sample")
    parser.add_argument("--pair", default="BTC/USD")
    parser.add_argument("--timeframe", default="5m")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/ohlcv/kraken"),
    )
    args = parser.parse_args(argv)
    try:
        rows = download_ohlcv(args.pair, args.timeframe, args.limit)
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"FAIL download: {exc}", file=sys.stderr)
        return 1
    if not rows:
        print("FAIL no data returned", file=sys.stderr)
        return 1
    safe_pair = args.pair.replace("/", "_")
    out_file = args.out / f"{safe_pair}-{args.timeframe}.csv"
    save_csv(rows, out_file)
    print(f"OK {len(rows)} candles -> {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
