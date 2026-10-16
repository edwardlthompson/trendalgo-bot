"""Worker pool (D2): cancel stops running jobs, and no child process is left behind."""

from __future__ import annotations

import math
import multiprocessing
import subprocess
import sys

import pytest

from trendalgo.device.jobs import engine_check_job, sleep_job
from trendalgo.device.workers import WorkerPool


def test_a_pool_needs_at_least_one_worker() -> None:
    with pytest.raises(ValueError, match="at least one worker"):
        WorkerPool(0)


def test_worker_modules_load_without_qt() -> None:
    """D1: a fresh interpreter that imports what a worker imports never loads PySide6."""
    code = (
        "import sys\n"
        "import trendalgo.device.__main__, trendalgo.device.jobs, trendalgo.device.workers\n"
        "print(any(name.startswith('PySide6') for name in sys.modules))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    assert result.stdout.strip() == "False"


def test_a_job_runs_in_a_worker_and_the_pool_shuts_down_clean() -> None:
    pool = WorkerPool(1)
    try:
        summary = pool.submit(engine_check_job, 3).get(timeout=120)
    finally:
        pool.shutdown()
    assert math.isfinite(summary["final_equity"])
    assert multiprocessing.active_children() == []


def test_cancel_stops_a_running_job_and_the_pool_recovers() -> None:
    pool = WorkerPool(1)
    try:
        pool.submit(sleep_job, 30)
        pool.cancel()
        assert multiprocessing.active_children() == []
        assert pool.submit(sleep_job, 0).get(timeout=120) == 0
    finally:
        pool.shutdown()
    assert multiprocessing.active_children() == []
