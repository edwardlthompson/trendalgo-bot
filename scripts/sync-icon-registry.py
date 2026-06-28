#!/usr/bin/env python3
"""Sync exchange + top-1000 coin icons into SQLite and web JSON registries."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from trendalgo.icons.store import IconStore
from trendalgo.icons.sync import migrate_coin_icons_local, sync_all, sync_coins, sync_exchanges


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync icon registry")
    parser.add_argument("--coins-only", action="store_true")
    parser.add_argument("--exchanges-only", action="store_true")
    parser.add_argument("--migrate-coins", action="store_true", help="Download local coin files from existing coins.json URLs")
    parser.add_argument("--refresh", action="store_true", help="Re-download all icon files")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()
    data_dir = Path(os.environ.get("TRENDALGO_DATA_DIR", "data"))
    store = IconStore(data_dir / "icon-registry.db")
    try:
        if args.exchanges_only:
            result = sync_exchanges(store, refresh=args.refresh)
        elif args.migrate_coins:
            result = migrate_coin_icons_local(store, refresh=args.refresh)
        elif args.coins_only:
            result = sync_coins(store, limit=args.limit, refresh=args.refresh)
        else:
            result = sync_all(coin_limit=args.limit, refresh=args.refresh)
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("Icon registry sync OK", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
