"""Bridge legacy JSON board/backtest payloads into results.db (ADR-0021)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from trendalgo.device.profile import RESULTS_DB
from trendalgo.results_store.ipc import handshake_payload, write_handshake
from trendalgo.results_store.schema import SCHEMA_VERSION
from trendalgo.results_store.store import ResultsStore


def _engine_version() -> str:
    try:
        from importlib.metadata import version

        return version("trendalgo-bot")
    except Exception:
        return "0.0.0-dev"


def touch_handshake(root: Path) -> None:
    write_handshake(
        root,
        handshake_payload(
            engine_version=_engine_version(),
            schema_version=SCHEMA_VERSION,
            catalog_hash="",
            results_db=RESULTS_DB,
        ),
    )


def publish_opportunity_rows(
    root: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    lane: str = "crypto",
) -> str | None:
    if not rows:
        return None
    touch_handshake(root)
    store = ResultsStore(root)
    try:
        run_id = store.start_run(
            "opportunity",
            lane=lane,
            engine_version=_engine_version(),
        )
        store.append_opportunity_rows(run_id, rows)
        store.finish_run(run_id)
        return run_id
    finally:
        store.close()


def publish_strategy_rows(
    root: Path,
    rows: Sequence[Mapping[str, Any]],
    *,
    pair: str = "",
    lane: str = "crypto",
) -> str | None:
    if not rows:
        return None
    touch_handshake(root)
    store = ResultsStore(root)
    try:
        run_id = store.start_run(
            "all_ta",
            lane=lane,
            pair=pair,
            engine_version=_engine_version(),
        )
        batch = 100
        for start in range(0, len(rows), batch):
            chunk = rows[start : start + batch]
            store.append_strategy_rows(run_id, chunk, start_id=start)
            store.set_job_state("all_ta", "running", run_id=run_id)
        store.set_job_state("all_ta", "done", run_id=run_id)
        store.finish_run(run_id)
        return run_id
    finally:
        store.close()
