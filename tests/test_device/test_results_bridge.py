"""Device → results.db bridge (ADR-0021)."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.last_pair_backtest import save_last_pair_backtest
from trendalgo.device.lts_scan_model import save_lts_rows
from trendalgo.results_store.store import ResultsStore


def test_save_lts_rows_also_publishes_opportunity_run(tmp_path: Path) -> None:
    save_lts_rows(
        tmp_path,
        [{"pair": "BTC/USD", "symbol": "BTC", "exchange": "kraken", "gain": 1.0}],
        lane="crypto",
    )
    store = ResultsStore(tmp_path)
    assert (tmp_path / "results.db").is_file()
    store.close()


def test_save_last_pair_backtest_publishes_strategy_batches(tmp_path: Path) -> None:
    rows = [{"strategy_id": f"s{i}", "pair": "ETH/USD", "net_pct": float(i)} for i in range(5)]
    save_last_pair_backtest(tmp_path, "ETH/USD", rows)
    store = ResultsStore(tmp_path)
    run = None
    cur = store._conn.execute(
        "SELECT run_id FROM runs WHERE kind='all_ta' ORDER BY started_at DESC LIMIT 1"
    )
    row = cur.fetchone()
    assert row is not None
    run = row["run_id"]
    assert store.count_strategy_rows(run) == 5
    store.close()
