"""Deepen seeds keep input order under a parallel ThreadPool."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd

from trendalgo.device.scanner_all_ta_prune import deepen_seeds
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="kraken",
        taker_pct=0.0026,
        maker_pct=0.0016,
        tier="test",
        source_url="",
        source="test",
    )


def test_deepen_seeds_preserves_order(monkeypatch: Any) -> None:
    frame = pd.DataFrame({"close": [1.0, 2.0, 3.0]})
    started: list[str] = []

    def fake_climb(
        _active: Any,
        seed: dict[str, Any],
        **_kw: Any,
    ) -> dict[str, Any]:
        sid = str(seed.get("strategy_id"))
        started.append(sid)
        # Finish middle seed last so completion order ≠ input order.
        if sid == "B":
            time.sleep(0.05)
        return {**seed, "optimized": True, "net_profit": 1.0}

    monkeypatch.setattr("trendalgo.device.scanner_all_ta_prune.climb_seed", fake_climb)
    monkeypatch.setattr(
        "trendalgo.device.scanner_all_ta_prune.pass2_worker_count",
        lambda: 4,
    )
    seeds = [
        {"strategy_id": "A", "timeframe": "1h", "net_profit": 1.0},
        {"strategy_id": "B", "timeframe": "1h", "net_profit": 2.0},
        {"strategy_id": "C", "timeframe": "1h", "net_profit": 3.0},
    ]
    out = deepen_seeds(
        frame,
        seeds,
        fee=_fee(),
        stake_usd=100.0,
        timeframe="1h",
        frames_by_tf={"1h": frame},
    )
    assert [r["strategy_id"] for r in out] == ["A", "B", "C"]
    assert set(started) == {"A", "B", "C"}


def test_catalog_accel_label_honest() -> None:
    from trendalgo.device.sim_accel_label import catalog_accel_label

    label = catalog_accel_label()
    assert "python(SIM-01)" in label
    assert "tsl_grid=" in label
