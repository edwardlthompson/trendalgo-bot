"""Portfolio sync + trading status load test CLI (CM-6, S20)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from trendalgo.exchanges.load_test import run_n_exchange_ops_validation


def main() -> int:
    report = run_n_exchange_ops_validation()
    out = Path(os.environ.get("TRENDALGO_LOAD_TEST_REPORT", "data/audit/load-test-portfolio.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    portfolio = report["portfolio_sync"]
    trading = report["trading_status"]
    if report["ok"]:
        print(
            f"OK   N-exchange ops: {portfolio['exchange_count']} portfolio sync "
            f"in {portfolio['elapsed_sec']}s; {trading['trading_exchange_count']} trading venues "
            f"(phase {trading['worldwide_trading_phase']})"
        )
        return 0
    print(
        f"FAIL N-exchange ops: portfolio_ok={portfolio['ok']} trading_ok={trading['ok']}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
