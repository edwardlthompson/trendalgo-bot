#!/usr/bin/env python3
"""Benchmark Kraken BTC/USD fleet backtest ($1000) with per-step timings."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "src") not in sys.path:
    sys.path.insert(0, str(_REPO / "src"))


def _fmt(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes, secs = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {secs}s"


class Benchmark:
    def __init__(self) -> None:
        self.t0 = time.monotonic()
        self.steps: list[dict[str, object]] = []
        self._last_phase: str | None = None
        self._phase_started = self.t0
        self._last_msg = 0
        self._tf_started: dict[str, float] = {}
        self._tf_done: set[str] = set()

    def elapsed(self) -> float:
        return time.monotonic() - self.t0

    def mark(self, name: str, **meta: object) -> None:
        now = self.elapsed()
        row = {"step": name, "elapsed_s": round(now, 3), **meta}
        self.steps.append(row)
        extra = " ".join(f"{k}={v}" for k, v in meta.items())
        print(f"[{_fmt(now):>8}] {name}" + (f"  ({extra})" if extra else ""))

    def observe(self, snap: dict) -> None:
        phase = str(snap.get("phase") or "pass1")
        if phase != self._last_phase:
            if self._last_phase is not None:
                self.mark(
                    f"phase_{self._last_phase}_done",
                    duration_s=round(time.monotonic() - self._phase_started, 3),
                )
            self.mark(f"phase_{phase}_start")
            self._last_phase = phase
            self._phase_started = time.monotonic()

        messages = snap.get("messages") or []
        for msg in messages[self._last_msg :]:
            text = str(msg)
            if text.startswith("OHLCV fetch ") and "…" in text:
                parts = text.split()
                tf = parts[4] if len(parts) > 4 else "?"
                self._tf_started[tf] = time.monotonic()
                self.mark("ohlcv_fetch_start", timeframe=tf)
            elif text.startswith("Timeframe ") and " done:" in text:
                tf = text.split()[1]
                started = self._tf_started.pop(tf, self.t0)
                self._tf_done.add(tf)
                self.mark(
                    "timeframe_pass1_done",
                    timeframe=tf,
                    duration_s=round(time.monotonic() - started, 3),
                )
            elif text.startswith("Pass 2:"):
                self.mark("optimize_params_announced")
            elif text.startswith("Pass 3:"):
                self.mark("optimize_tsl_announced")
            elif text.startswith("Fleet complete:"):
                self.mark("fleet_complete_message")
        self._last_msg = len(messages)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exchange", default="kraken")
    parser.add_argument("--pair", default="BTC/USD")
    parser.add_argument("--stake", type=float, default=1000.0)
    parser.add_argument(
        "--market-source",
        default=os.environ.get("TRENDALGO_MARKET_SOURCE", "synthetic"),
        help="synthetic (fast smoke) or live exchange fetch",
    )
    parser.add_argument("--timeout", type=int, default=7200, help="max wait seconds")
    parser.add_argument("--json-out", default="", help="write benchmark JSON here")
    args = parser.parse_args()

    data_dir = Path(tempfile.mkdtemp(prefix="fleet-bench-"))
    os.environ["TRENDALGO_DATA_DIR"] = str(data_dir)
    os.environ["TRENDALGO_MARKET_SOURCE"] = args.market_source
    os.environ.setdefault("TRENDALGO_FLEET_FETCH_DELAY_MS", "0")

    from trendalgo.backtest.fleet_runner import get_fleet_runner
    from trendalgo.backtest.ta_fleet import all_strategies
    from trendalgo.constants.timeframes import TRADINGVIEW_INTERVALS

    bench = Benchmark()
    bench.mark(
        "preflight",
        exchange=args.exchange,
        pair=args.pair,
        stake_usd=args.stake,
        market_source=args.market_source,
        strategies=len(all_strategies()),
        timeframes=len(TRADINGVIEW_INTERVALS),
        pass1_combos=len(all_strategies()) * len(TRADINGVIEW_INTERVALS),
    )

    runner = get_fleet_runner(data_dir)
    t_start = time.monotonic()
    snap = runner.start(args.exchange, args.pair, args.stake)
    bench.mark(
        "fleet_start",
        job_id=snap.get("id"),
        total_combinations=snap.get("total_combinations"),
        duration_s=round(time.monotonic() - t_start, 3),
    )

    active: dict | None = snap
    deadline = time.monotonic() + args.timeout
    last_progress = -1
    while time.monotonic() < deadline:
        active = runner.snapshot()
        if active:
            bench.observe(active)
            pct = int(active.get("progress_pct") or 0)
            if pct != last_progress and pct % 10 == 0:
                bench.mark(
                    "progress",
                    phase=active.get("phase"),
                    pct=pct,
                    completed=active.get("completed"),
                    total=active.get("total_combinations"),
                    current=active.get("current_test"),
                )
                last_progress = pct
            if active.get("status") in ("complete", "error"):
                break
        time.sleep(0.05)

    if not active:
        bench.mark("fail", reason="no_snapshot")
        return 1

    bench.mark(
        "terminal_status",
        status=active.get("status"),
        phase=active.get("phase"),
        elapsed_server_s=active.get("elapsed_seconds"),
    )
    if active.get("status") == "error":
        bench.mark("fail", error=active.get("error"))
        return 1

    # Replay full message log for steps missed during fast runs.
    replay = Benchmark()
    replay.t0 = bench.t0
    replay.observe({"messages": active.get("messages") or [], "phase": "pass1"})
    for row in replay.steps:
        if row not in bench.steps:
            bench.steps.append(row)

    summary = active.get("summary") or {}
    final_top10 = (
        summary.get("final_top10") or summary.get("optimized_top10") or active.get("top10") or []
    )
    bench.mark("verify_top10", count=len(final_top10))
    if len(final_top10) < 10:
        bench.mark("fail", reason="top10_incomplete", count=len(final_top10))
        return 1

    bench.mark("top10_results")
    for row in final_top10[:10]:
        print(
            f"  #{row.get('rank')} {row.get('strategy_id')} @{row.get('timeframe')} "
            f"net=${float(row.get('net_profit', 0)):.2f} "
            f"tsl={float(row.get('optimal_tsl_pct', row.get('trailing_stop_pct', 0)) or 0) * 100:.0f}% "
            f"params={row.get('params')}"
        )

    bh = summary.get("buy_and_hold") or {}
    bench.mark("verify_buy_hold", net=bh.get("net_profit"))

    history = runner.list_history(limit=1)
    bench.mark("verify_history", runs=history.get("total", 0))
    if not history.get("runs"):
        bench.mark("fail", reason="history_empty")
        return 1

    best = final_top10[0]
    ta_params = {k: v for k, v in (best.get("params") or {}).items() if isinstance(v, (int, float))}
    t_bot = time.monotonic()
    from trendalgo.bots.orchestrator import BotOrchestrator  # noqa: PLC0415

    orch = BotOrchestrator(data_dir / "bots.db")
    bot_id = orch.add_bot(
        label="BenchBot-1",
        strategy_id=str(best["strategy_id"]),
        pair=args.pair,
        equity_usd=args.stake,
        exchange=args.exchange,
        timeframe=str(best["timeframe"]),
        enabled=False,
        ta_params=ta_params,
    )
    bench.mark(
        "create_bot_from_top1",
        bot_id=bot_id,
        strategy=best.get("strategy_id"),
        timeframe=best.get("timeframe"),
        duration_s=round(time.monotonic() - t_bot, 3),
    )

    if bench._last_phase is not None:
        bench.mark(
            f"phase_{bench._last_phase}_done",
            duration_s=round(time.monotonic() - bench._phase_started, 3),
        )
    bench.mark("benchmark_complete", total_s=round(bench.elapsed(), 3))

    report = {
        "exchange": args.exchange,
        "pair": args.pair,
        "stake_usd": args.stake,
        "market_source": args.market_source,
        "total_seconds": round(bench.elapsed(), 3),
        "steps": bench.steps,
        "top10_count": len(final_top10),
        "job_id": active.get("id"),
    }
    if args.json_out:
        out = Path(args.json_out)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {out}")

    print("\n=== Step timing summary ===")
    for row in bench.steps:
        if row["step"].startswith(
            ("phase_", "ohlcv_", "timeframe_", "fleet_", "verify_", "create_", "benchmark_")
        ):
            print(f"  {row['step']}: {row.get('duration_s', row['elapsed_s'])}s")

    print(f"\nOK benchmark passed in {_fmt(bench.elapsed())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
