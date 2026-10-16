"""BacktestCounter: an exact, monotonic count of finished backtests for one sweep."""

from __future__ import annotations

import multiprocessing
import queue
import time
from typing import Any

from trendalgo.lts_vendor.backtesting.backtest_counter import (
    DONE,
    EVENT,
    STEP,
    BacktestCounter,
)


class _ListSource:
    """Stand-in for a multiprocessing queue: ``get_nowait`` raises ``queue.Empty`` when dry."""

    def __init__(self, items: list[object]) -> None:
        self._items = list(items)

    def get_nowait(self) -> object:
        if not self._items:
            raise queue.Empty
        return self._items.pop(0)


def _counter(
    symbols: list[str], *, timeframes: int, strategies: int
) -> tuple[BacktestCounter, list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    counter = BacktestCounter(
        symbols, timeframes=timeframes, strategies=strategies, emit=events.append
    )
    return counter, events


def test_total_is_coins_times_timeframes_times_strategies() -> None:
    counter, events = _counter(["BTC", "ETH", "SOL"], timeframes=2, strategies=13)
    assert counter.total == 78  # 3 coins x 2 timeframes x (12 indicators + B&H)
    counter.flush()
    assert events == [{"event": EVENT, "done": 0, "total": 78}]


def test_steps_count_up_and_emit_only_when_the_count_changes() -> None:
    counter, events = _counter(["BTC"], timeframes=1, strategies=3)
    counter.flush()
    counter.apply((STEP, "BTC"))
    counter.apply((STEP, "BTC"))
    counter.flush()
    counter.flush()  # unchanged: no second event
    assert counter.done == 2
    assert events == [
        {"event": EVENT, "done": 0, "total": 3},
        {"event": EVENT, "done": 2, "total": 3},
    ]


def test_a_coin_never_counts_more_than_its_planned_backtests() -> None:
    counter, _ = _counter(["BTC"], timeframes=1, strategies=3)
    for _ in range(5):
        counter.apply((STEP, "BTC"))
    assert counter.done == 3


def test_closing_a_coin_early_tops_it_up_to_its_full_share() -> None:
    counter, _ = _counter(["BTC", "ETH"], timeframes=1, strategies=3)
    counter.apply((STEP, "BTC"))
    assert counter.apply((DONE, "BTC")) is True
    assert counter.done == 3
    # Late steps for a closed coin are ignored, so the total cannot pass the plan.
    assert counter.apply((STEP, "BTC")) is False
    assert counter.done == 3


def test_done_for_an_unknown_or_closed_coin_changes_nothing() -> None:
    counter, _ = _counter(["BTC"], timeframes=1, strategies=3)
    assert counter.apply((DONE, "XRP")) is False
    assert counter.apply((DONE, "BTC")) is True
    assert counter.apply((DONE, "BTC")) is False
    assert counter.done == 3


def test_malformed_messages_are_ignored() -> None:
    counter, _ = _counter(["BTC"], timeframes=1, strategies=3)
    for junk in ["step", ("step",), (STEP, "BTC", "extra"), ("unknown", "BTC"), None]:
        assert counter.apply(junk) is False
    assert counter.done == 0


def test_close_finishes_every_open_coin_and_emits_the_final_count() -> None:
    counter, events = _counter(["BTC", "ETH"], timeframes=1, strategies=3)
    counter.apply((STEP, "BTC"))
    counter.close()
    assert counter.done == 6
    assert events[-1] == {"event": EVENT, "done": 6, "total": 6}


def test_drain_applies_everything_ready_and_emits_once() -> None:
    counter, events = _counter(["BTC", "ETH"], timeframes=1, strategies=2)
    counter.flush()
    source = _ListSource([(STEP, "BTC"), (STEP, "ETH"), "junk", (DONE, "BTC")])
    counter.drain(source)
    assert counter.done == 3  # BTC topped up to 2, plus one ETH step
    assert events == [
        {"event": EVENT, "done": 0, "total": 4},
        {"event": EVENT, "done": 3, "total": 4},
    ]


def test_in_process_sink_applies_and_emits_each_change() -> None:
    counter, events = _counter(["BTC"], timeframes=1, strategies=2)
    counter.flush()
    sink = counter.in_process_sink()
    sink.put_nowait((STEP, "BTC"))
    sink.put_nowait((DONE, "BTC"))
    assert [event["done"] for event in events] == [0, 1, 2]


def test_finish_coin_reports_a_timed_out_coin_at_once() -> None:
    counter, events = _counter(["BTC", "ETH"], timeframes=1, strategies=4)
    counter.finish_coin("BTC")
    assert events[-1] == {"event": EVENT, "done": 4, "total": 8}
    counter.finish_coin("BTC")  # already closed: nothing moves
    assert counter.done == 4


def test_no_planned_work_is_a_quiet_no_op() -> None:
    counter, events = _counter([], timeframes=2, strategies=13)
    assert counter.total == 0
    counter.apply((STEP, "BTC"))
    counter.close()
    assert events == [{"event": EVENT, "done": 0, "total": 0}]


def test_duplicate_symbols_count_once() -> None:
    counter, _ = _counter(["BTC", "BTC"], timeframes=1, strategies=3)
    assert counter.total == 3


def test_real_multiprocessing_queue_is_drained_without_losing_messages() -> None:
    mp_context = multiprocessing.get_context()
    step_queue = mp_context.Queue()
    counter, _ = _counter(["BTC"], timeframes=1, strategies=3)
    try:
        for _ in range(2):
            step_queue.put((STEP, "BTC"))
        step_queue.put((DONE, "BTC"))
        deadline = time.monotonic() + 10.0
        while counter.done < 3 and time.monotonic() < deadline:
            counter.drain(step_queue)
            time.sleep(0.01)  # the queue's feeder thread may still be writing
        assert counter.done == 3
    finally:
        step_queue.close()
        step_queue.join_thread()
