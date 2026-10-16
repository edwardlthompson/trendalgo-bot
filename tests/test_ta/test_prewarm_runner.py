"""TaPrewarmRunner: finishing a job must not deadlock snapshot() (the log path takes the same lock)."""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from trendalgo.ta import prewarm


def _bot(pair: str) -> dict[str, Any]:
    return {"id": pair, "pair": pair, "timeframe": "60", "strategy_id": "rsi"}


def _call_with_timeout(fn: Any, timeout_s: float = 5.0) -> Any:
    box: dict[str, Any] = {}
    worker = threading.Thread(target=lambda: box.update(value=fn()), daemon=True)
    worker.start()
    worker.join(timeout_s)
    assert not worker.is_alive(), "snapshot() blocked: prewarm thread deadlocked on its own lock"
    return box["value"]


def test_completed_prewarm_job_does_not_block_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prewarm, "_prewarm_one", lambda _data_dir, bot: f"{bot['pair']} done")
    runner = prewarm.TaPrewarmRunner(tmp_path)
    runner.start([_bot("BTC/USD"), _bot("ETH/USD")])
    assert runner._thread is not None
    runner._thread.join(timeout=5)

    snap = _call_with_timeout(runner.snapshot)

    assert snap is not None
    assert snap["status"] == "complete"
    assert snap["completed_fingerprints"] == 2
    assert "TA signal prewarm complete." in snap["messages"]


def test_parallel_mode_prewarms_every_fingerprint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The thread pool only runs off Windows; fake the platform on this module's sys reference only.
    monkeypatch.setattr(prewarm, "TA_PARALLEL", True)
    monkeypatch.setattr(prewarm, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(prewarm, "_prewarm_one", lambda _data_dir, bot: bot["pair"])
    runner = prewarm.TaPrewarmRunner(tmp_path)
    runner.start([_bot("BTC/USD"), _bot("ETH/USD")])
    assert runner._thread is not None
    runner._thread.join(timeout=5)

    snap = _call_with_timeout(runner.snapshot)

    assert snap is not None
    assert snap["status"] == "complete"
    assert snap["completed_fingerprints"] == 2


def test_start_with_no_bots_completes_without_a_thread(tmp_path: Path) -> None:
    runner = prewarm.TaPrewarmRunner(tmp_path)
    runner.start([])
    assert runner._thread is None

    snap = _call_with_timeout(runner.snapshot)

    assert snap is not None
    assert snap["status"] == "complete"
    assert snap["messages"] == ["No bot fingerprints to prewarm."]


def test_start_while_running_returns_the_active_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = threading.Event()

    def _wait(_data_dir: Path, bot: dict[str, Any]) -> str:
        release.wait(5)
        return bot["pair"]

    monkeypatch.setattr(prewarm, "_prewarm_one", _wait)
    runner = prewarm.TaPrewarmRunner(tmp_path)
    first = runner.start([_bot("BTC/USD")])
    second = _call_with_timeout(lambda: runner.start([_bot("ETH/USD")]))
    release.set()
    assert runner._thread is not None
    runner._thread.join(timeout=5)

    assert second["id"] == first["id"]
    assert second["total_fingerprints"] == 1


def test_duplicate_bot_fingerprints_are_prewarmed_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        prewarm, "_prewarm_one", lambda _data_dir, bot: calls.append(bot["pair"]) or bot["pair"]
    )
    runner = prewarm.TaPrewarmRunner(tmp_path)
    started = runner.start([_bot("BTC/USD"), _bot("BTC/USD")])
    assert runner._thread is not None
    runner._thread.join(timeout=5)

    assert started["total_fingerprints"] == 1
    assert calls == ["BTC/USD"]


def test_short_price_series_is_skipped_not_computed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        prewarm, "bot_chart_payload", lambda _bot, _data_dir: {"ohlcv": [{"ts": 1}] * 3}
    )

    label = prewarm._prewarm_one(tmp_path, _bot("BTC/USD"))

    assert label == "BTC/USD (skipped — short series)"


def test_failed_prewarm_job_reports_error_without_deadlock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(_data_dir: Path, _bot: dict[str, Any]) -> str:
        raise RuntimeError("chart missing")

    monkeypatch.setattr(prewarm, "_prewarm_one", _boom)
    runner = prewarm.TaPrewarmRunner(tmp_path)
    runner.start([_bot("BTC/USD")])
    assert runner._thread is not None
    runner._thread.join(timeout=5)

    snap = _call_with_timeout(runner.snapshot)

    assert snap is not None
    assert snap["status"] == "error"
    assert snap["error"] == "chart missing"
    assert any("TA prewarm failed" in message for message in snap["messages"])
