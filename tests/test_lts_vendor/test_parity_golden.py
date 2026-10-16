"""p2-parity-harness: golden trade lists, no signal flips on the 500-bar window, TA-Lib per arch.

The engine and the streaming port must both reproduce the golden trade lists, bar for bar. The
port feeds the host's 500-bar window signals (L5). TA-Lib indicators stay out of live until the
amd64 and arm64 captures match (L6). Fixtures: see parity_support.py.
"""

from __future__ import annotations

import json

import pytest

from trendalgo.lts_vendor.backtesting.signals import talib_available

from .engine_golden_support import INDICATORS, SEEDS, _midpoint, make_frame
from .parity_support import (
    CASES,
    GOLDEN_BARS,
    TALIB_FIXTURE,
    TALIB_INDICATORS,
    TRADE_FIXTURE,
    case_key,
    current_arch,
    engine_trades,
    port_trades,
    talib_digests,
    trade_rows,
    window_flips,
)

GOLDEN = json.loads(TRADE_FIXTURE.read_text(encoding="utf-8"))["trades"]
TALIB_DATA = json.loads(TALIB_FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("indicator", "seed", "config_name"), CASES)
def test_engine_trades_match_the_golden_list(indicator: str, seed: int, config_name: str) -> None:
    expected = GOLDEN[case_key(indicator, seed, config_name)]
    assert trade_rows(engine_trades(indicator, seed, config_name)) == expected


@pytest.mark.parametrize(("indicator", "seed", "config_name"), CASES)
def test_port_with_window_signals_matches_the_golden_list(
    indicator: str, seed: int, config_name: str
) -> None:
    expected = GOLDEN[case_key(indicator, seed, config_name)]
    assert trade_rows(port_trades(indicator, seed, config_name)) == expected


def test_golden_fixture_covers_every_case_and_every_exit_reason() -> None:
    assert set(GOLDEN) == {case_key(*case) for case in CASES}
    reasons = {row["exit_reason"] for rows in GOLDEN.values() for row in rows}
    assert {"sell_signal", "trailing_stop_loss", "take_profit", "end_of_data"} <= reasons


def _flipped_bars(indicator: str, seed: int) -> list[int]:
    return window_flips(indicator, make_frame(GOLDEN_BARS, seed), _midpoint(indicator))


@pytest.mark.parametrize("indicator", INDICATORS)
@pytest.mark.parametrize("seed", SEEDS)
def test_no_signal_flips_once_the_window_is_full(indicator: str, seed: int) -> None:
    flips = _flipped_bars(indicator, seed)
    assert not flips, f"{len(flips)} bar(s) flip on the window, first at bar {flips[0]}"


@pytest.mark.skipif(not talib_available(), reason="TA-Lib not installed on this machine")
@pytest.mark.parametrize("indicator", TALIB_INDICATORS)
@pytest.mark.parametrize("seed", SEEDS)
def test_talib_indicators_have_no_flips_either(indicator: str, seed: int) -> None:
    flips = _flipped_bars(indicator, seed)
    assert not flips, f"{len(flips)} bar(s) flip on the window, first at bar {flips[0]}"


def test_talib_indicators_stay_out_of_live_until_both_architectures_match() -> None:
    assert set(TALIB_DATA["talib_required"]) == set(TALIB_INDICATORS)
    captures = [entry["digests"] for _, entry in sorted(TALIB_DATA["architectures"].items())]
    matched = all(c is not None for c in captures) and all(c == captures[0] for c in captures)
    live_talib = set(TALIB_DATA["live_v1"]) & set(TALIB_INDICATORS)
    assert not live_talib or matched, f"{sorted(live_talib)} need matching amd64 and arm64 captures"


@pytest.mark.skipif(not talib_available(), reason="TA-Lib not installed on this machine")
def test_talib_digests_match_this_architectures_capture() -> None:
    capture = TALIB_DATA["architectures"].get(current_arch(), {}).get("digests")
    if capture is None:
        pytest.skip(f"no TA-Lib capture for {current_arch()} yet (see fixtures/talib_arch.json)")
    assert talib_digests() == capture
