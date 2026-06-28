"""Bot-scoped OHLCV cache warmup — only pairs/timeframes used by saved bots."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from trendalgo.bots.limits import chart_lookback_seconds
from trendalgo.constants.timeframes import (
    ccxt_interval_seconds,
    normalize_tv_interval,
    timeframe_for_fetch,
)
from trendalgo.market.service import PriceHistoryService
from trendalgo.market.symbols import base_symbol
from trendalgo.ta.prewarm import schedule_ta_prewarm_after_ohlcv

ProgressCallback = Callable[[str], None]


@dataclass
class WarmupSeriesTarget:
    pair: str
    tv_timeframe: str
    fetch_timeframe: str
    lookback_seconds: int
    bot_labels: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        bots = ", ".join(self.bot_labels[:3])
        suffix = f" +{len(self.bot_labels) - 3}" if len(self.bot_labels) > 3 else ""
        return f"{self.pair} · {self.tv_timeframe} ({bots}{suffix})"


def collect_bot_series(bots: list[dict[str, Any]]) -> list[WarmupSeriesTarget]:
    """Unique (pair, timeframe) series referenced by saved bots — not the full exchange catalog."""
    seen: dict[tuple[str, str], WarmupSeriesTarget] = {}
    for bot in bots:
        pair = str(bot.get("pair") or "BTC/USD")
        tv_tf = normalize_tv_interval(str(bot.get("timeframe") or "60"))
        fetch_tf = timeframe_for_fetch(tv_tf)
        key = (pair.upper(), fetch_tf)
        label = str(bot.get("label") or f"Bot-{bot.get('id', '?')}")
        if key not in seen:
            seen[key] = WarmupSeriesTarget(
                pair=pair,
                tv_timeframe=tv_tf,
                fetch_timeframe=fetch_tf,
                lookback_seconds=chart_lookback_seconds(tv_tf),
                bot_labels=[label],
            )
        elif label not in seen[key].bot_labels:
            seen[key].bot_labels.append(label)
    return list(seen.values())


@dataclass
class WarmupJob:
    id: str
    status: str  # idle | running | complete | error
    total_series: int = 0
    completed_series: int = 0
    current_series: str = ""
    bars_cached: int = 0
    bars_downloaded: int = 0
    messages: list[str] = field(default_factory=list)
    series_results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        pct = 0
        if self.total_series > 0:
            base = self.completed_series / self.total_series
            if self.status == "running" and self.current_series:
                base += 0.5 / self.total_series
            pct = min(100, int(base * 100))
        return {
            "id": self.id,
            "status": self.status,
            "progress_pct": pct,
            "total_series": self.total_series,
            "completed_series": self.completed_series,
            "current_series": self.current_series,
            "bars_cached": self.bars_cached,
            "bars_downloaded": self.bars_downloaded,
            "messages": self.messages[-40:],
            "series_results": self.series_results,
            "error": self.error,
        }


class OhlcvWarmupRunner:
    """Background OHLCV download for bot pairs only (shared cache per pair+timeframe)."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._lock = threading.Lock()
        self._active: WarmupJob | None = None
        self._thread: threading.Thread | None = None

    def snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            return self._active.to_dict() if self._active else None

    def start(self, bots: list[dict[str, Any]]) -> dict[str, Any]:
        with self._lock:
            if self._active and self._active.status == "running":
                return self._active.to_dict()
            targets = collect_bot_series(bots)
            if not targets:
                idle = WarmupJob(id="none", status="complete", total_series=0)
                idle.messages.append("No bots configured — nothing to cache.")
                self._active = idle
                return idle.to_dict()
            job = WarmupJob(
                id=uuid.uuid4().hex[:12],
                status="running",
                total_series=len(targets),
            )
            job.messages.append(
                f"Warming OHLCV cache for {len(targets)} unique pair/timeframe series "
                f"from {len(bots)} saved bot(s). Exchange-wide pairs are skipped."
            )
            self._active = job
            self._thread = threading.Thread(
                target=self._run,
                args=(job, targets, bots),
                daemon=True,
                name="ohlcv-warmup",
            )
            self._thread.start()
            return job.to_dict()

    def _log(self, job: WarmupJob, message: str) -> None:
        job.messages.append(message)

    def _run(
        self, job: WarmupJob, targets: list[WarmupSeriesTarget], bots: list[dict[str, Any]]
    ) -> None:
        service = PriceHistoryService(self._data_dir / "prices.db")
        try:
            for target in targets:
                with self._lock:
                    job.current_series = target.label
                self._log(
                    job, f"▶ {target.label} — lookback {target.lookback_seconds // 3600}h window"
                )

                until = datetime.now(UTC)
                since = until - timedelta(seconds=target.lookback_seconds)
                sym = base_symbol(target.pair).upper()
                before = service.ohlcv_cache_count(sym, target.fetch_timeframe, since, until)
                candles = service.get_ohlcv(
                    target.pair,
                    target.fetch_timeframe,
                    since,
                    until,
                    on_progress=lambda kind, msg: self._on_series_progress(job, kind, msg),
                )
                after = len(candles)
                downloaded = max(0, after - before)
                with self._lock:
                    job.bars_cached += after
                    job.completed_series += 1
                    job.series_results.append(
                        {
                            "pair": target.pair,
                            "timeframe": target.tv_timeframe,
                            "bars": after,
                            "downloaded": downloaded,
                            "bots": target.bot_labels,
                        }
                    )
                self._log(
                    job,
                    f"✓ {target.pair} {target.tv_timeframe}: {after:,} bars in cache "
                    f"({downloaded:,} newly downloaded)",
                )
            with self._lock:
                job.status = "complete"
                job.current_series = ""
                self._log(
                    job, "OHLCV cache warmup complete. Charts and TA will reuse stored candles."
                )
            schedule_ta_prewarm_after_ohlcv(self._data_dir, bots)
        except Exception as exc:
            with self._lock:
                job.status = "error"
                job.error = str(exc)
                self._log(job, f"✗ Warmup failed: {exc}")

    def _on_series_progress(self, job: WarmupJob, kind: str, message: str) -> None:
        with self._lock:
            if kind == "downloaded":
                parts = message.replace(",", "").split()
                if parts and parts[0].isdigit():
                    job.bars_downloaded += int(parts[0])
            self._log(job, message)


_runners: dict[str, OhlcvWarmupRunner] = {}


def get_warmup_runner(data_dir: Path) -> OhlcvWarmupRunner:
    key = str(data_dir.resolve())
    if key not in _runners:
        _runners[key] = OhlcvWarmupRunner(data_dir)
    return _runners[key]


def cache_status_for_bots(data_dir: Path, bots: list[dict[str, Any]]) -> dict[str, Any]:
    service = PriceHistoryService(data_dir / "prices.db")
    series = collect_bot_series(bots)
    rows: list[dict[str, Any]] = []
    for target in series:
        until = datetime.now(UTC)
        since = until - timedelta(seconds=target.lookback_seconds)
        sym = base_symbol(target.pair).upper()
        cached = service.ohlcv_cache_count(sym, target.fetch_timeframe, since, until)
        step = ccxt_interval_seconds(target.fetch_timeframe)
        expected = max(1, target.lookback_seconds // max(step, 1))
        pct = min(100, int(cached / expected * 100)) if expected else 0
        rows.append(
            {
                "pair": target.pair,
                "timeframe": target.tv_timeframe,
                "cached_bars": cached,
                "expected_bars": expected,
                "coverage_pct": pct,
                "bots": target.bot_labels,
            }
        )
    return {
        "bot_scoped": True,
        "bot_count": len(bots),
        "unique_series": len(series),
        "series": rows,
    }
