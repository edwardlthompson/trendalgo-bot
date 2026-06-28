"""Smoke: portfolio performance graph + top-10 benchmark."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API = os.environ.get("TRENDALGO_SMOKE_API", "http://127.0.0.1:8000/api/v1")
RANGES = ("1y", "6m", "3m", "1m", "14d", "7d", "24h")


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post(path: str) -> dict:
    req = urllib.request.Request(f"{API}{path}", method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


RANGES = ("1y", "6m", "3m", "1m", "14d", "7d", "24h")
DAILY_MIN = {"1y": 300, "6m": 150, "3m": 75, "1m": 25}
HOURLY_MIN = {"14d": 300, "7d": 140, "24h": 20}


def main() -> int:
    try:
        overview = _get("/portfolio/overview")
        print(
            f"net_worth=${overview['net_worth_usd']} history_dates={len(overview.get('snapshot_dates', []))}"
        )

        sync = _post("/portfolio/sync")
        print(f"sync-all venues={sync.get('exchange_count')} mode={sync.get('mode')}")

        for rng in RANGES:
            perf = _get(f"/portfolio/performance?range={rng}")
            pts = perf.get("points") or []
            top10 = perf.get("top10_index") or []
            cmp_ = perf.get("comparison") or {}
            gran = perf.get("granularity", "?")
            source = perf.get("source", "?")
            print(
                f"range={rng} gran={gran} source={source} points={len(pts)} top10={len(top10)} "
                f"alpha={cmp_.get('alpha_pct')}%"
            )
            min_pts = HOURLY_MIN.get(rng, DAILY_MIN.get(rng, 2))
            if len(pts) < min_pts:
                print(
                    f"FAIL: expected >={min_pts} points for {rng}, got {len(pts)}", file=sys.stderr
                )
                return 1
            if rng in DAILY_MIN and gran != "1d":
                print(f"FAIL: {rng} should use daily granularity", file=sys.stderr)
                return 1
            if rng in HOURLY_MIN and gran != "1h":
                print(f"FAIL: {rng} should use hourly granularity", file=sys.stderr)
                return 1

        print("Portfolio graph smoke OK")
        return 0
    except urllib.error.URLError as exc:
        print(f"Smoke failed — is API running on {API}? {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
