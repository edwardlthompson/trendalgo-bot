"""Background TA fleet backtest runner (all strategies × all timeframes)."""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from trendalgo.backtest.fleet_config import (
    FLEET_LOOKBACK_DAYS,
    FLEET_LOOKBACK_SECONDS,
    OPTIMIZE_TOP_N,
    PASS12_TRAILING_STOP_PCT,
    fleet_lookback_seconds,
)
from trendalgo.backtest.fleet_optimize import estimate_optimize_combos, optimize_top_rows
from trendalgo.backtest.fleet_store import FleetStore
from trendalgo.backtest.fleet_tsl_optimize import estimate_tsl_combos, optimize_tsl_for_rows
from trendalgo.backtest.ta_fleet import (
    all_strategies,
    backtest_one,
    buy_and_hold_row,
    merge_rank,
)
from trendalgo.constants.timeframes import TRADINGVIEW_INTERVALS, timeframe_for_fetch
from trendalgo.exchanges.fees import get_fee_schedule
from trendalgo.exchanges.pairs import list_pairs_for_exchange
from trendalgo.exchanges.registry import get_entry
from trendalgo.market.service import PriceHistoryService
from trendalgo.ta.cache import ohlcv_list_to_df
from trendalgo.ta.indicator_cache import reset_indicator_cache

_FETCH_DELAY_MS = int(os.environ.get("TRENDALGO_FLEET_FETCH_DELAY_MS", "250"))


class FleetPreflightError(ValueError):
    pass


def validate_fleet_request(exchange_id: str, pair: str) -> tuple[str, str]:
    eid = exchange_id.lower().strip()
    try:
        get_entry(eid)
    except KeyError as exc:
        raise FleetPreflightError(f"unknown exchange: {exchange_id}") from exc
    try:
        get_fee_schedule(eid)
    except KeyError as exc:
        raise FleetPreflightError(f"no fee schedule for exchange: {exchange_id}") from exc
    base_pair = pair.upper().strip()
    allowed = {p.upper() for p in list_pairs_for_exchange(eid)}
    if base_pair not in allowed:
        raise FleetPreflightError(f"pair {pair} is not tradable on {exchange_id}")
    return eid, base_pair


def _points_to_dicts(points: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "time": p.time,
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume,
        }
        for p in points
    ]


def _top5_for_bots(rows: list[dict[str, Any]], pair: str, exchange_id: str) -> list[dict[str, Any]]:
    top = merge_rank(rows, top_n=5)
    out: list[dict[str, Any]] = []
    for row in top:
        out.append(
            {
                "strategy_id": row["strategy_id"],
                "indicator": row["strategy_id"],
                "profit_total": row["net_profit"],
                "trades": row["trades"],
                "timeframe": row["timeframe"],
                "pair": pair,
                "exchange_id": exchange_id,
            }
        )
    return out


@dataclass
class FleetJob:
    id: str
    status: str  # running | complete | error
    exchange_id: str
    pair: str
    stake_usd: float
    total: int = 0
    completed: int = 0
    phase: str = "pass1"
    current_timeframe: str = ""
    current_strategy: str = ""
    eta_seconds: int | None = None
    messages: list[str] = field(default_factory=list)
    recent_tests: list[dict[str, Any]] = field(default_factory=list)
    top10: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    _started_at: float = field(default_factory=time.monotonic)
    _combo_ms: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        pct = int((self.completed / self.total) * 100) if self.total else 0
        elapsed = int(time.monotonic() - self._started_at)
        current = (
            f"{self.current_strategy} @ {self.current_timeframe}"
            if self.current_strategy and self.current_timeframe
            else ""
        )
        return {
            "id": self.id,
            "status": self.status,
            "phase": self.phase,
            "exchange_id": self.exchange_id,
            "pair": self.pair,
            "stake_usd": self.stake_usd,
            "lookback_days": FLEET_LOOKBACK_DAYS,
            "lookback_seconds": FLEET_LOOKBACK_SECONDS,
            "total_combinations": self.total,
            "completed": self.completed,
            "progress_pct": pct,
            "elapsed_seconds": elapsed,
            "current_timeframe": self.current_timeframe,
            "current_strategy": self.current_strategy,
            "current_test": current,
            "eta_seconds": self.eta_seconds,
            "messages": self.messages[-60:],
            "recent_tests": self.recent_tests[-30:],
            "top10": self.top10,
            "summary": self.summary,
            "error": self.error,
        }


class TaFleetBacktestRunner:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._lock = threading.Lock()
        self._active: FleetJob | None = None
        self._thread: threading.Thread | None = None
        self._store = FleetStore(data_dir / "ta_fleet.db")
        self._market = PriceHistoryService(data_dir / "prices.db")
        self._last_completed: dict[str, Any] | None = None

    def consume_completed(self) -> dict[str, Any] | None:
        with self._lock:
            payload = self._last_completed
            self._last_completed = None
            return payload

    def latest_from_store(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        group_by: str | None = None,
    ) -> dict[str, Any] | None:
        return self._store.latest(limit=limit, offset=offset, group_by=group_by)

    def snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            return self._active.to_dict() if self._active else None

    def list_history(self, *, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        return self._store.list_runs(limit=limit, offset=offset)

    def get_history_run(self, job_id: str) -> dict[str, Any] | None:
        return self._store.get_run(job_id)

    def start(
        self,
        exchange_id: str,
        pair: str,
        stake_usd: float = 1000.0,
        *,
        strategies: tuple[str, ...] | None = None,
        timeframes: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        eid, normalized_pair = validate_fleet_request(exchange_id, pair)
        strat_list = strategies or all_strategies()
        tf_list = timeframes or TRADINGVIEW_INTERVALS
        with self._lock:
            if self._active and self._active.status == "running":
                return self._active.to_dict()
            job = FleetJob(
                id=uuid.uuid4().hex[:12],
                status="running",
                exchange_id=eid,
                pair=normalized_pair,
                stake_usd=stake_usd,
                total=len(strat_list) * len(tf_list),
            )
            job.messages.append(
                f"Fleet pass 1: {len(strat_list)} strategies × {len(tf_list)} timeframes · "
                f"{FLEET_LOOKBACK_DAYS}d window (all TFs) · TSL optimized in pass 3"
            )
            self._active = job
            self._thread = threading.Thread(
                target=self._run,
                args=(job, strat_list, tf_list),
                daemon=True,
                name="ta-fleet",
            )
            self._thread.start()
            return job.to_dict()

    def _log(self, job: FleetJob, message: str) -> None:
        with self._lock:
            job.messages.append(message)

    def _tick(
        self,
        job: FleetJob,
        *,
        strategy: str,
        timeframe: str,
        row: dict[str, Any] | None,
        reason: str | None,
        elapsed_ms: float,
    ) -> None:
        with self._lock:
            job.completed += 1
            job.current_strategy = strategy
            job.current_timeframe = timeframe
            job._combo_ms.append(elapsed_ms)
            if len(job._combo_ms) > 80:
                job._combo_ms = job._combo_ms[-80:]
            remaining = max(0, job.total - job.completed)
            avg_ms = sum(job._combo_ms) / len(job._combo_ms)
            job.eta_seconds = int((remaining * avg_ms) / 1000) if job._combo_ms else None
            status = "ok" if row else (reason or "skip")
            job.recent_tests.append(
                {
                    "strategy_id": strategy,
                    "timeframe": timeframe,
                    "status": status,
                    "net_profit": row.get("net_profit") if row else None,
                    "trades": row.get("trades") if row else 0,
                    "phase": job.phase,
                }
            )
            if len(job.recent_tests) > 50:
                job.recent_tests = job.recent_tests[-50:]

    def _run(
        self,
        job: FleetJob,
        strategies: tuple[str, ...],
        timeframes: tuple[str, ...],
    ) -> None:
        fee = get_fee_schedule(job.exchange_id)
        all_results: list[dict[str, Any]] = []
        skips: dict[str, int] = {}
        timeframes_skipped: list[str] = []
        ohlcv_by_tf: dict[str, list[dict[str, Any]]] = {}
        fetch_tf_map: dict[str, str] = {}
        buy_hold: dict[str, Any] | None = None
        lookback = fleet_lookback_seconds()
        until = datetime.now(UTC)
        since = until - timedelta(seconds=lookback)
        try:
            for tv_tf in timeframes:
                fetch_tf = timeframe_for_fetch(tv_tf)
                fetch_tf_map[tv_tf] = fetch_tf
                self._log(
                    job,
                    f"OHLCV fetch {job.exchange_id} {job.pair} {tv_tf} "
                    f"({FLEET_LOOKBACK_DAYS}d / {fetch_tf})…",
                )
                try:
                    points = self._market.get_ohlcv(
                        job.pair,
                        fetch_tf,
                        since,
                        until,
                        exchange_id=job.exchange_id,
                        on_progress=lambda _kind, msg: self._log(job, msg),
                    )
                    if _FETCH_DELAY_MS > 0:
                        time.sleep(_FETCH_DELAY_MS / 1000.0)
                except Exception as exc:
                    self._log(job, f"Skipped {tv_tf}: OHLCV fetch failed ({exc})")
                    timeframes_skipped.append(tv_tf)
                    continue
                ohlcv = _points_to_dicts(points)
                ohlcv_by_tf[tv_tf] = ohlcv
                if len(ohlcv) < 50:
                    self._log(job, f"Skipped {tv_tf}: only {len(ohlcv)} bars")
                    timeframes_skipped.append(tv_tf)
                    continue
                if buy_hold is None:
                    df_bh = ohlcv_list_to_df(ohlcv, pair=job.pair, fetch_tf=fetch_tf)
                    buy_hold = buy_and_hold_row(
                        df_bh,
                        lookback_seconds=lookback,
                        stake_usd=job.stake_usd,
                        fee=fee,
                    )
                reset_indicator_cache()
                df = ohlcv_list_to_df(ohlcv, pair=job.pair, fetch_tf=fetch_tf)
                tf_hits = 0
                for sid in strategies:
                    t0 = time.monotonic()
                    row, reason = backtest_one(
                        df,
                        sid,
                        fee,
                        job.stake_usd,
                        timeframe=tv_tf,
                        lookback_seconds=lookback,
                        trailing_stop_pct=PASS12_TRAILING_STOP_PCT,
                        phase="pass1",
                    )
                    elapsed_ms = (time.monotonic() - t0) * 1000
                    self._tick(
                        job,
                        strategy=sid,
                        timeframe=tv_tf,
                        row=row,
                        reason=reason,
                        elapsed_ms=elapsed_ms,
                    )
                    if row:
                        all_results.append(row)
                        tf_hits += 1
                        self._log(
                            job,
                            f"[{job.completed}/{job.total}] {sid} @ {tv_tf} → "
                            f"${row['net_profit']:.2f} net ({row['trades']} trades)",
                        )
                    else:
                        key = reason or "compute_error"
                        skips[key] = skips.get(key, 0) + 1
                        self._log(
                            job,
                            f"[{job.completed}/{job.total}] {sid} @ {tv_tf} → skip ({key})",
                        )
                    with self._lock:
                        job.top10 = merge_rank(all_results, top_n=10)
                self._log(job, f"Timeframe {tv_tf} done: {tf_hits}/{len(strategies)} ranked")

            top10 = merge_rank(all_results, top_n=OPTIMIZE_TOP_N)
            opt_total = estimate_optimize_combos(top10)
            with self._lock:
                job.phase = "optimize_params"
                job.total = job.completed + opt_total
            self._log(job, f"Pass 2: param optimize top {len(top10)} ({opt_total} trials, TSL=0)…")

            def on_opt(label: str, trial: dict[str, Any] | None, reason: str | None) -> None:
                parts = label.split("@", 1)
                sid = parts[0].replace("opt ", "").strip()
                tf = parts[1].split(" ", 1)[0].strip() if len(parts) > 1 else ""
                self._tick(
                    job,
                    strategy=sid,
                    timeframe=tf,
                    row=trial,
                    reason=reason,
                    elapsed_ms=1.0,
                )
                if trial:
                    self._log(
                        job,
                        f"[params {job.completed}/{job.total}] {sid} @ {tf} → ${trial['net_profit']:.2f}",
                    )

            optimized = optimize_top_rows(
                top10,
                ohlcv_by_tf,
                fee=fee,
                stake_usd=job.stake_usd,
                pair=job.pair,
                fetch_tf_by_tv=fetch_tf_map,
                lookback_seconds=lookback,
                on_trial=on_opt,
            )

            tsl_total = estimate_tsl_combos(optimized)
            with self._lock:
                job.phase = "optimize_tsl"
                job.total = job.completed + tsl_total
            self._log(
                job,
                f"Pass 3: TSL sweep 0–20% (step 2%) on top {len(optimized)} ({tsl_total} trials)…",
            )

            def on_tsl(label: str, trial: dict[str, Any] | None, reason: str | None) -> None:
                parts = label.split("@", 1)
                sid = parts[0].replace("tsl ", "").strip()
                tf = parts[1].split(" ", 1)[0].strip() if len(parts) > 1 else ""
                self._tick(
                    job,
                    strategy=sid,
                    timeframe=tf,
                    row=trial,
                    reason=reason,
                    elapsed_ms=1.0,
                )
                if trial:
                    tsl_pct = trial.get("trailing_stop_pct", 0)
                    self._log(
                        job,
                        f"[tsl {job.completed}/{job.total}] {sid} @ {tf} "
                        f"TSL={tsl_pct * 100:.0f}% → ${trial['net_profit']:.2f}",
                    )

            final_top10 = optimize_tsl_for_rows(
                optimized,
                ohlcv_by_tf,
                fee=fee,
                stake_usd=job.stake_usd,
                pair=job.pair,
                fetch_tf_by_tv=fetch_tf_map,
                lookback_seconds=lookback,
                on_trial=on_tsl,
            )

            ranked = merge_rank(all_results, top_n=100)
            summary = {
                "skipped": sum(skips.values()),
                "errors_by_reason": skips,
                "timeframes_skipped": timeframes_skipped,
                "combinations_run": job.completed,
                "fee_taker_pct": fee.taker_pct,
                "exchange_id": job.exchange_id,
                "pair": job.pair,
                "lookback_days": FLEET_LOOKBACK_DAYS,
                "lookback_seconds": lookback,
                "buy_and_hold": buy_hold,
                "top10_pass1": top10,
                "optimized_top10": optimized,
                "final_top10": final_top10,
            }
            self._store.save_run(job.id, job.exchange_id, job.pair, job.stake_usd, summary, ranked)
            with self._lock:
                job.status = "complete"
                job.phase = "complete"
                job.summary = summary
                job.top10 = final_top10 or optimized or top10
                job.completed = job.total
                job.eta_seconds = 0
                self._last_completed = {
                    "job_id": job.id,
                    "exchange_id": job.exchange_id,
                    "pair": job.pair,
                    "stake_usd": job.stake_usd,
                    "summary": summary,
                    "rankings": ranked,
                    "top10": final_top10 or optimized or top10,
                    "final_top10": final_top10,
                    "top5": _top5_for_bots(
                        final_top10 or optimized or top10, job.pair, job.exchange_id
                    ),
                    "best": final_top10[0]
                    if final_top10
                    else ((optimized or top10)[0] if (optimized or top10) else None),
                    "buy_and_hold": buy_hold,
                }
            bh_net = buy_hold.get("net_profit") if buy_hold else None
            fin_net = final_top10[0]["net_profit"] if final_top10 else 0.0
            bh_msg = f"buy & hold ${bh_net:.2f}" if bh_net is not None else "buy & hold n/a"
            self._log(
                job,
                f"Fleet complete: final top ${fin_net:.2f} · {bh_msg}",
            )
        except Exception as exc:
            with self._lock:
                job.status = "error"
                job.error = str(exc)
            self._log(job, f"Fleet error: {exc}")


_runners: dict[str, TaFleetBacktestRunner] = {}


def get_fleet_runner(data_dir: Path) -> TaFleetBacktestRunner:
    key = str(data_dir.resolve())
    if key not in _runners:
        _runners[key] = TaFleetBacktestRunner(data_dir)
    return _runners[key]
