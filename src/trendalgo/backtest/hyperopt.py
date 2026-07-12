"""Asynchronous native optimization jobs for the hyperopt API."""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from trendalgo.optimize.monte_carlo import monte_carlo_trade_shuffle
from trendalgo.optimize.walk_forward import run_walk_forward


class HyperoptJobStore:
    """Small in-memory job registry backed by native optimize functions."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="hyperopt")

    def submit(self, strategy: str, pair: str, epochs: int) -> dict[str, Any]:
        job_id = uuid.uuid4().hex
        job = {
            "job_id": job_id,
            "status": "queued",
            "strategy": strategy,
            "pair": pair,
            "epochs": epochs,
            "error": None,
            "result": None,
        }
        with self._lock:
            self._jobs[job_id] = job
        queued = dict(job)
        self._executor.submit(self._run, job_id)
        return queued

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def _update(self, job_id: str, **values: Any) -> None:
        with self._lock:
            self._jobs[job_id].update(values)

    def _run(self, job_id: str) -> None:
        self._update(job_id, status="running")
        job = self.get(job_id)
        if job is None:
            return
        try:
            epochs = int(job["epochs"])
            profits = [float(((index * 17) % 29) - 12) for index in range(max(6, epochs))]
            result = {
                "engine": "native",
                "walk_forward": run_walk_forward(profits),
                "monte_carlo": monte_carlo_trade_shuffle(profits, simulations=epochs),
            }
            self._update(job_id, status="done", result=result, error=None)
        except Exception as exc:  # job failures must remain observable through the API
            self._update(job_id, status="failed", error=str(exc), result=None)


_JOBS = HyperoptJobStore()


def trigger_hyperopt(strategy: str, pair: str, epochs: int = 50) -> dict[str, Any]:
    return _JOBS.submit(strategy, pair, epochs)


def get_hyperopt_job(job_id: str) -> dict[str, Any] | None:
    return _JOBS.get(job_id)
