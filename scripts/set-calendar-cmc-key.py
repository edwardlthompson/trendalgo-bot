#!/usr/bin/env python3
"""Save a CoinMarketCal API key into Windows Credential Manager (PF-H1).

Usage (repo root):
  uv run python scripts/set-calendar-cmc-key.py

Never pass the key on the command line or commit it.
"""

from __future__ import annotations

import getpass
import sys


def main() -> int:
    if sys.platform != "win32":
        print("Windows only (Credential Manager).", file=sys.stderr)
        return 1
    print("CoinMarketCal key → TrendAlgo/calendar-coinmarketcal")
    if sys.stdin.isatty():
        print("Paste the key, then Enter (input is hidden).")
        secret = getpass.getpass("CMC API key: ").strip()
        if not secret:
            # Some IDE terminals break getpass; fall back to visible one-shot.
            secret = input("CMC API key (visible): ").strip()
    else:
        secret = sys.stdin.readline().strip()
    if not secret:
        print("Empty key — aborted.", file=sys.stderr)
        return 1
    from trendalgo.device.calendar.vault import read_cmc_key, write_cmc_key

    write_cmc_key(secret)
    got = read_cmc_key()
    if not got:
        print("FAIL: wrote but read-back empty.", file=sys.stderr)
        return 1
    if got != secret:
        print("FAIL: read-back mismatch.", file=sys.stderr)
        return 1
    print(f"OK saved (len={len(got)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
