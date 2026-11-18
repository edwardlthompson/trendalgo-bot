"""Per-unit EWMA timing ledger + wall ETA helpers."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.backtest_scan_eta import (
    remaining_from_units,
    remaining_seconds,
    wall_coins_prior_s,
)
from trendalgo.device.scan_unit_timing import (
    UnitSample,
    UnitTimingLedger,
    estimate_catalog_wall_s,
    load_ledger,
    lookup_unit_s,
    record_units,
    save_ledger,
    top_slowest,
)


def test_record_and_lookup_fallback(tmp_path: Path) -> None:
    ledger = UnitTimingLedger()
    record_units(
        ledger,
        [
            UnitSample("RSI", "1h", "BTC/USD", 1.0),
            UnitSample("RSI", "1h", "BTC/USD", 3.0),
            UnitSample("MACD", "5m", "ETH/USD", 2.0),
        ],
    )
    save_ledger(tmp_path, ledger)
    loaded = load_ledger(tmp_path)
    rsi = lookup_unit_s(loaded, "RSI", "1h")
    assert 1.0 < rsi < 3.0
    # Unknown TF for known strategy falls back to strategy mean.
    assert lookup_unit_s(loaded, "RSI", "4h") == lookup_unit_s(loaded, "RSI", "1h")
    assert lookup_unit_s(loaded, "UNKNOWN", "1h") > 0


def test_catalog_wall_divides_by_workers() -> None:
    ledger = UnitTimingLedger(global_unit_s=1.0)
    units = [("A", "1h"), ("B", "1h"), ("C", "1h"), ("D", "1h")]
    serial = estimate_catalog_wall_s(ledger, units, workers=1, fallback=1.0)
    parallel = estimate_catalog_wall_s(ledger, units, workers=4, fallback=1.0)
    assert serial == 4.0
    assert parallel == 1.0


def test_top_slowest_and_wall_coins() -> None:
    samples = [
        UnitSample("A", "1h", "X", 0.5),
        UnitSample("B", "1h", "X", 3.0),
        UnitSample("C", "1h", "X", 1.0),
    ]
    top = top_slowest(samples, 2)
    assert [u.strategy for u in top] == ["B", "C"]
    assert wall_coins_prior_s(per_coin_s=10.0, n_coins=5, coin_workers=2) == 30.0
    assert wall_coins_prior_s(per_coin_s=10.0, n_coins=4, coin_workers=4) == 10.0


def test_stamped_eta_preferred_over_flat() -> None:
    flat = remaining_seconds(elapsed_s=10.0, done=5, total=10, prior_s=100.0)
    stamped = remaining_seconds(
        elapsed_s=10.0, done=5, total=10, prior_s=100.0, stamped_remaining_s=12.0
    )
    assert stamped.remaining_s == 12.0
    assert flat.remaining_s is not None
    assert stamped.remaining_s != flat.remaining_s
    unit = remaining_from_units(unfinished_priors_s=8.0, workers=2)
    assert unit.remaining_s == 4.0
