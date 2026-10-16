"""p5-shadow-divergence: every mismatch gets one class, and a clean run needs 14 days (E5, L1)."""

from __future__ import annotations

import math

import pytest

from trendalgo.botd.shadow_divergence import classify_run
from trendalgo.botd.shadow_report import REQUIRED_CLEAN_DAYS, Divergence, build_report
from trendalgo.lts_vendor.backtesting.models import Trade

BARS = [f"2026-09-01 {hour:02d}:00:00" for hour in range(8, 16)]
ENTRY = "2026-09-01 10:00:00"
EXIT = "2026-09-01 13:00:00"
LATER = "2026-09-01 14:00:00"


def _trade(
    *,
    entry: str = ENTRY,
    entry_price: float = 100.0,
    quantity: float = 2.0,
    exit_time: str = EXIT,
    exit_price: float = 105.0,
    reason: str = "sell_signal",
) -> Trade:
    return Trade(
        entry_time=entry,
        entry_price=entry_price,
        entry_fee=0.2,
        quantity=quantity,
        exit_time=exit_time,
        exit_price=exit_price,
        exit_fee=0.2,
        pnl_dollars=9.6,
        pnl_pct=4.8,
        exit_reason=reason,
    )


def _classify(
    expected: list[Trade],
    observed: list[Trade],
    *,
    bars_observed: list[str] | None = None,
    bps: float = 0.0,
) -> list[Divergence]:
    observed_bars = BARS if bars_observed is None else bars_observed
    return classify_run(BARS, observed_bars, expected, observed, price_bps=bps)


def _kinds(found: list[Divergence]) -> list[str]:
    return [item.kind for item in found]


def test_identical_runs_have_no_divergence() -> None:
    assert _classify([_trade()], [_trade()]) == []


def test_an_entry_only_the_engine_made_is_a_signal_divergence() -> None:
    assert _kinds(_classify([_trade()], [])) == ["signal"]


def test_an_entry_only_the_shadow_run_made_is_a_signal_divergence() -> None:
    assert _kinds(_classify([], [_trade()])) == ["signal"]


def test_a_sell_signal_on_another_bar_is_a_signal_divergence() -> None:
    assert _kinds(_classify([_trade()], [_trade(exit_time=LATER)])) == ["signal"]


def test_a_take_profit_against_a_trailing_stop_is_a_stop_divergence() -> None:
    engine = _trade(reason="take_profit", exit_price=102.0)
    shadow = _trade(reason="trailing_stop_loss", exit_price=102.0)
    assert _kinds(_classify([engine], [shadow])) == ["stop"]


def test_a_stop_exit_in_another_hour_is_a_stop_divergence() -> None:
    # L1: the monitor can exit an hour later than the engine's intrabar stop.
    engine = _trade(reason="trailing_stop_loss", exit_time="2026-09-01 12:00:00")
    shadow = _trade(reason="trailing_stop_loss", exit_time=EXIT)
    assert _kinds(_classify([engine], [shadow])) == ["stop"]


def test_an_entry_price_gap_inside_the_tolerance_passes() -> None:
    engine = _trade(entry_price=100.0)
    shadow = _trade(entry_price=100.005)  # 0.5 bps
    assert _classify([engine], [shadow], bps=1.0) == []


def test_an_entry_price_gap_outside_the_tolerance_is_a_fill_divergence() -> None:
    engine = _trade(entry_price=100.0)
    shadow = _trade(entry_price=100.005)
    assert _kinds(_classify([engine], [shadow], bps=0.1)) == ["fill"]


def test_a_quantity_gap_is_a_fill_divergence() -> None:
    assert _kinds(_classify([_trade(quantity=2.0)], [_trade(quantity=1.0)])) == ["fill"]


def test_a_signal_exit_price_gap_is_a_fill_divergence() -> None:
    assert _kinds(_classify([_trade(exit_price=105.0)], [_trade(exit_price=104.0)])) == ["fill"]


def test_a_stop_exit_price_gap_is_a_stop_divergence() -> None:
    engine = _trade(reason="trailing_stop_loss", exit_price=95.0)
    shadow = _trade(reason="trailing_stop_loss", exit_price=94.0)
    assert _kinds(_classify([engine], [shadow])) == ["stop"]


def test_a_missing_bar_and_the_trade_it_affects_are_data_divergences() -> None:
    observed_bars = [bar for bar in BARS if bar != "2026-09-01 12:00:00"]
    found = _classify([_trade()], [_trade(exit_time=LATER)], bars_observed=observed_bars)
    assert _kinds(found) == ["data", "data"]


def test_a_repeated_bar_is_a_data_divergence() -> None:
    observed_bars = [*BARS, BARS[2]]
    assert _kinds(_classify([_trade()], [_trade()], bars_observed=observed_bars)) == ["data"]


def test_an_out_of_order_bar_is_a_data_divergence() -> None:
    observed_bars = [BARS[0], BARS[2], BARS[1], *BARS[3:]]
    assert _kinds(_classify([_trade()], [_trade()], bars_observed=observed_bars)) == ["data"]


def test_an_exit_reason_the_port_never_emits_is_a_data_divergence() -> None:
    assert _kinds(_classify([_trade(reason="unknown")], [_trade()])) == ["data"]


def test_two_trades_on_one_entry_bar_are_a_data_divergence() -> None:
    assert _kinds(_classify([_trade(), _trade()], [_trade()])) == ["data"]


def test_a_missing_price_is_never_hidden() -> None:
    assert _kinds(_classify([_trade()], [_trade(entry_price=math.nan)], bps=1e9)) == ["fill"]


def test_a_zero_base_price_is_never_hidden() -> None:
    engine = _trade(entry_price=0.0)
    assert _kinds(_classify([engine], [_trade(entry_price=1.0)], bps=1e9)) == ["fill"]


def test_the_tolerance_must_be_zero_or_more() -> None:
    with pytest.raises(ValueError, match="price_bps"):
        _classify([], [], bps=-1.0)


def test_every_divergence_gets_one_known_class() -> None:
    expected = [_trade(), _trade(entry="2026-09-01 11:00:00", reason="take_profit")]
    observed = [
        _trade(entry_price=101.0),
        _trade(entry="2026-09-01 11:00:00", reason="trailing_stop_loss"),
    ]
    found = _classify(expected, observed)
    assert found
    assert all(item.kind in {"signal", "fill", "stop", "data"} for item in found)


def test_clean_needs_fourteen_days_and_no_divergence() -> None:
    assert build_report([], days=REQUIRED_CLEAN_DAYS).is_clean()
    assert not build_report([], days=REQUIRED_CLEAN_DAYS - 1).is_clean()
    one_fill = [Divergence("fill", ENTRY, "entry price")]
    assert not build_report(one_fill, days=30).is_clean()


def test_the_report_counts_each_class() -> None:
    found = [
        Divergence("fill", ENTRY, "x"),
        Divergence("fill", ENTRY, "y"),
        Divergence("data", ENTRY, "z"),
    ]
    report = build_report(found, days=3)
    assert (report.signal, report.fill, report.stop, report.data, report.total) == (0, 2, 0, 1, 3)
    assert "fill 2" in report.describe()
    assert "clean: no" in report.describe()


def test_negative_days_are_refused() -> None:
    with pytest.raises(ValueError, match="days"):
        build_report([], days=-1)
