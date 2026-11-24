"""results.db + IPC contract (ADR-0021)."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.results_store import PROTOCOL_VERSION, ResultsStore, handshake_payload
from trendalgo.results_store.ipc import read_handshake, write_handshake
from trendalgo.results_store.schema import SCHEMA_VERSION


def test_schema_and_progressive_strategy_writes(tmp_path: Path) -> None:
    store = ResultsStore(tmp_path)
    assert store.schema_version() == SCHEMA_VERSION
    run_id = store.start_run("all_ta", lane="crypto", pair="BTC/USD", engine_version="1.19.0")
    store.set_job_state("scan-1", "running", run_id=run_id)
    n1 = store.append_strategy_rows(
        run_id,
        [{"strategy_id": "rsi", "pair": "BTC/USD", "score": 1.0}],
        start_id=0,
    )
    n2 = store.append_strategy_rows(
        run_id,
        [{"strategy_id": "macd", "pair": "BTC/USD", "score": 2.0}],
        start_id=1,
    )
    assert n1 == 1 and n2 == 1
    assert store.count_strategy_rows(run_id) == 2
    store.set_job_state("scan-1", "paused", run_id=run_id)
    assert store.job_state("scan-1") == "paused"
    store.finish_run(run_id)
    rows = list(store.iter_strategy_rows(run_id, limit=10))
    assert [r["strategy_id"] for r in rows] == ["rsi", "macd"]
    store.close()


def test_migrate_lts_scan_rows_json(tmp_path: Path) -> None:
    path = tmp_path / "lts_scan_rows.json"
    path.write_text(
        json.dumps([{"pair": "ETH/USD", "gain": 3.1}, {"pair": "BTC/USD", "gain": 1.2}]),
        encoding="utf-8",
    )
    store = ResultsStore(tmp_path)
    run_id = store.migrate_opportunity_json(path, lane="crypto")
    assert run_id is not None
    store.close()


def test_ipc_handshake_roundtrip(tmp_path: Path) -> None:
    hs = handshake_payload(
        engine_version="1.19.0",
        schema_version=SCHEMA_VERSION,
        catalog_hash="abc",
        results_db="results.db",
        pid=42,
    )
    write_handshake(tmp_path, hs)
    loaded = read_handshake(tmp_path)
    assert loaded is not None
    assert loaded.protocol_version == PROTOCOL_VERSION
    assert loaded.compatible_with_shell(PROTOCOL_VERSION, SCHEMA_VERSION)
    assert not loaded.compatible_with_shell(PROTOCOL_VERSION + 1, SCHEMA_VERSION)
