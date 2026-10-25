"""CLI smoke: one All-TA pair scan for frozen / packaging verification."""

from __future__ import annotations

from collections import Counter

from trendalgo.device.last_pair_backtest import save_last_pair_backtest
from trendalgo.device.pair_strategy_scan_job import pair_strategy_scan_job
from trendalgo.device.profile import profile_dir


def run_smoke_backtest(pair: str) -> int:
    """Run ``pair_strategy_scan_job`` and print counts. Exit 0 when rows are returned."""
    text = str(pair or "").strip().upper()
    if "/" not in text:
        print(f"FAIL pair must look like BTC/USD, got {pair!r}")
        return 1
    root = profile_dir()
    print(f"smoke-backtest {text} root={root}")
    try:
        payload = pair_strategy_scan_job(root, text)
    except Exception as exc:
        print(f"FAIL scan: {exc}")
        return 1
    rows = payload.get("rows") if isinstance(payload, dict) else payload
    market_context = payload.get("market_context") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        print("FAIL no rows")
        return 1
    reasons: Counter[str] = Counter()
    traded = 0
    for row in rows:
        skip = str(row.get("skip_reason") or "").strip()
        trades = row.get("trades")
        n = 0
        if trades not in (None, "-"):
            try:
                n = int(str(trades))
            except (TypeError, ValueError):
                n = 0
        if n > 0 and not skip:
            traded += 1
            reasons["ok"] += 1
        else:
            reasons[skip or "empty"] += 1
    save_last_pair_backtest(
        root,
        text,
        rows,
        market_context=market_context if isinstance(market_context, dict) else None,
    )
    print(f"OK rows={len(rows)} traded={traded}")
    print("skip_summary", dict(reasons.most_common(12)))
    return 0
