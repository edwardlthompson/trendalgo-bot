"""Portfolio sync load test CLI (CM-6, S17)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from trendalgo.exchanges.load_test import run_load_test


def main() -> int:
    report = run_load_test()
    out = Path(os.environ.get("TRENDALGO_LOAD_TEST_REPORT", "data/audit/load-test-portfolio.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["ok"]:
        print(
            f"OK   portfolio load test: {report['exchange_count']} exchanges "
            f"in {report['elapsed_sec']}s (< {report['max_sec']}s)"
        )
        return 0
    print(
        f"FAIL portfolio load test: count={report['exchange_count']} "
        f"elapsed={report['elapsed_sec']}s",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
