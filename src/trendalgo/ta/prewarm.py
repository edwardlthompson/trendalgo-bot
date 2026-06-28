"""Background TA signal precompute after OHLCV warmup."""

from __future__ import annotations

import os
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from trendalgo.bots.chart import bot_chart_payload
from trendalgo.constants.timeframes import timeframe_for_fetch
from trendalgo.ta.cache import TaFingerprint, get_ta_signal_cache, ohlcv_list_to_df

TA_PARALLEL = os.environ.get("TRENDALGO_TA_PARALLEL", "0") == "1"


@dataclass
class TaPrewarmJob:
    id: str
    status: str  # idle | running | complete | error
    total: int = 0
    completed: int = 0
    messages: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        pct = int((self.completed / self.total) * 100) if self.total else 100
        return {
            "id": self.id,
            "status": self.status,
            "progress_pct": pct,
            "total_fingerprints": self.total,
            "completed_fingerprints": self.completed,
            "messages": self.messages[-40:],
            "parallel": TA_PARALLEL and not sys.platform.startswith("win"),
            "error": self.error,
        }


class TaPrewarmRunner:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._lock = threading.Lock()
        self._active: TaPrewarmJob | None = None
        self._thread: threading.Thread | None = None

    def snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            return self._active.to_dict() if self._active else None

    def start(self, bots: list[dict[str, Any]]) -> dict[str, Any]:
        with self._lock:
            if self._active and self._active.status == "running":
                return self._active.to_dict()
            targets = _unique_bot_targets(bots)
            job = TaPrewarmJob(id=uuid.uuid4().hex[:12], status="running", total=len(targets))
            if not targets:
                job.status = "complete"
                job.messages.append("No bot fingerprints to prewarm.")
                self._active = job
                return job.to_dict()
            job.messages.append(f"Precomputing TA signals for {len(targets)} unique fingerprint(s).")
            self._active = job
            self._thread = threading.Thread(
                target=self._run,
                args=(job, targets),
                daemon=True,
                name="ta-prewarm",
            )
            self._thread.start()
            return job.to_dict()

    def _log(self, job: TaPrewarmJob, message: str) -> None:
        with self._lock:
            job.messages.append(message)

    def _run(self, job: TaPrewarmJob, targets: list[dict[str, Any]]) -> None:
        try:
            use_parallel = TA_PARALLEL and not sys.platform.startswith("win") and len(targets) > 1
            if use_parallel:
                workers = min(4, max(1, len(targets)))
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = [pool.submit(_prewarm_one, self._data_dir, bot) for bot in targets]
                    for fut in as_completed(futures):
                        label = fut.result()
                        with self._lock:
                            job.completed += 1
                        self._log(job, f"✓ {label}")
            else:
                for bot in targets:
                    label = _prewarm_one(self._data_dir, bot)
                    with self._lock:
                        job.completed += 1
                    self._log(job, f"✓ {label}")
            with self._lock:
                job.status = "complete"
                self._log(job, "TA signal prewarm complete.")
        except Exception as exc:
            with self._lock:
                job.status = "error"
                job.error = str(exc)
                self._log(job, f"✗ TA prewarm failed: {exc}")


def _unique_bot_targets(bots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[TaFingerprint] = set()
    out: list[dict[str, Any]] = []
    for bot in bots:
        fp = TaFingerprint.from_bot(bot)
        if fp in seen:
            continue
        seen.add(fp)
        out.append(bot)
    return out


def _prewarm_one(data_dir: Path, bot: dict[str, Any]) -> str:
    payload = bot_chart_payload(bot, data_dir)
    ohlcv = payload["ohlcv"]
    if len(ohlcv) < 10:
        return f"{bot.get('label', bot.get('id'))} (skipped — short series)"
    tf = str(bot.get("timeframe") or "60")
    fetch_tf = timeframe_for_fetch(tf)
    df = ohlcv_list_to_df(ohlcv, pair=str(bot["pair"]), fetch_tf=fetch_tf)
    cache = get_ta_signal_cache()
    cache.get_or_compute_signals(df, ohlcv, bot)
    fp = TaFingerprint.from_bot(bot)
    return f"{fp.pair} · {fp.timeframe} · {fp.strategy_id}"


_prewarm_runners: dict[str, TaPrewarmRunner] = {}


def get_ta_prewarm_runner(data_dir: Path) -> TaPrewarmRunner:
    key = str(data_dir.resolve())
    if key not in _prewarm_runners:
        _prewarm_runners[key] = TaPrewarmRunner(data_dir)
    return _prewarm_runners[key]


def schedule_ta_prewarm_after_ohlcv(data_dir: Path, bots: list[dict[str, Any]]) -> None:
    get_ta_prewarm_runner(data_dir).start(bots)
