#!/usr/bin/env python3
"""Pull exchange fees from public documentation pages into data/exchange_fees.db."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync exchange fee schedules from public fee pages"
    )
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("TRENDALGO_DATA_DIR", "data"),
        help="TrendAlgo data directory (default: data or TRENDALGO_DATA_DIR)",
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Seed from config/exchange_fees.json without fetching fee pages",
    )
    args = parser.parse_args()
    os.environ["TRENDALGO_DATA_DIR"] = str(Path(args.data_dir).resolve())

    from trendalgo.exchanges.fee_store import get_fee_store, reset_fee_store
    from trendalgo.exchanges.fee_sync import ensure_fee_db_ready, sync_exchange_fees

    reset_fee_store()
    store = get_fee_store()
    ensure_fee_db_ready(store, on_log=print)
    if args.seed_only:
        print(f"Seeded {store.count()} venues (no website fetch)")
        return 0

    summary = sync_exchange_fees(store, on_log=print)
    print(
        f"Done: {len(summary['updated'])} updated, "
        f"{len(summary['unchanged'])} unchanged, "
        f"{len(summary.get('fallback', []))} fallback, "
        f"{len(summary['failed'])} failed"
    )
    if summary["updated"]:
        print("Updated:", ", ".join(summary["updated"]))
    if summary.get("fallback"):
        print("Fallback (documented seed):", ", ".join(summary["fallback"]))
    if summary["failed"]:
        for row in summary["failed"]:
            print(f"  FAIL {row['exchange_id']}: {row['error']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
