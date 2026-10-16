"""±10 brute force + TF defaults sweep."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.hill_climb_brute import PM10, brute_pm_axes, brute_tf_defaults


def test_brute_pm10_tries_neighbors(monkeypatch: Any) -> None:
    seen: list[int] = []

    def trial_fn(
        _f: Any, _sid: str, params: dict[str, Any], _tsl: float, **_k: Any
    ) -> dict[str, Any]:
        val = int(params["entry_level"])
        seen.append(val)
        return {
            "strategy_id": "RSI",
            "net_profit": float(val),
            "params": dict(params),
            "trailing_stop_pct": 0.01,
            "timeframe": "1h",
        }

    monkeypatch.setattr(
        "trendalgo.backtest.hill_climb_brute.climb_axes",
        lambda _sid, _p: [("entry_level", 1.0, 5.0, 50.0, True)],
    )
    seed = {"entry_level": 30}
    best = {"net_profit": 0.0, "params": seed}
    params, best_out, net = brute_pm_axes(
        None,  # type: ignore[arg-type]
        "RSI",
        dict(seed),
        tsl=0.01,
        fee=None,  # type: ignore[arg-type]
        stake=1000.0,
        tf="1h",
        best=best,
        best_net=0.0,
        trial_fn=trial_fn,
        radius=10,
    )
    assert PM10 == 10
    assert set(seen) >= set(range(20, 41)) - {30}
    assert int(params["entry_level"]) == 40
    assert net == 40.0
    assert best_out["net_profit"] == 40.0


def test_brute_tf_defaults_picks_best() -> None:
    idx = pd.date_range("2024-01-01", periods=8, freq="h", tz="UTC")
    close = pd.Series([100.0] * 8, index=idx)
    frame = pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": 1.0},
        index=idx,
    )
    frames = {"1h": frame, "4h": frame}

    def trial_fn(
        _f: Any, sid: str, _params: dict[str, Any], _tsl: float, *, tf: str, **_k: Any
    ) -> dict[str, Any]:
        net = 4.0 if tf == "4h" else 1.0
        return {
            "strategy_id": sid,
            "net_profit": net,
            "params": {},
            "trailing_stop_pct": 0.01,
            "timeframe": tf,
        }

    best = {"net_profit": 0.0, "timeframe": "1h", "params": {}}
    tf, _active, best_out, net = brute_tf_defaults(
        frames,
        "RSI",
        {},
        tsl=0.01,
        fee=None,  # type: ignore[arg-type]
        stake=1000.0,
        best=best,
        best_net=0.0,
        trial_fn=trial_fn,
    )
    assert tf == "4h"
    assert net == 4.0
    assert best_out["timeframe"] == "4h"
