"""E8: one shared client per key, calls never overlap, and nonces never repeat."""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from trendalgo.exchanges import private_client
from trendalgo.exchanges.private_client import MonotonicNonce, SerializedExchange, ccxt_client
from trendalgo.exchanges.registry import get_entry


def test_nonce_never_repeats_while_the_clock_is_stuck() -> None:
    nonce = MonotonicNonce(lambda: 1000)
    assert [nonce(), nonce(), nonce()] == [1000, 1001, 1002]


def test_nonce_follows_the_clock_when_it_moves_forward() -> None:
    clock = iter([1000, 5000])
    nonce = MonotonicNonce(lambda: next(clock))
    assert [nonce(), nonce()] == [1000, 5000]


def test_nonce_never_goes_backwards_when_the_clock_steps_back() -> None:
    clock = iter([5000, 1000])
    nonce = MonotonicNonce(lambda: next(clock))
    assert [nonce(), nonce()] == [5000, 5001]


class _SlowExchange:
    """Stands in for ccxt. A private call sleeps, so unserialized calls would overlap."""

    def __init__(self) -> None:
        self.in_flight = 0
        self.max_in_flight = 0
        self.nonces: list[int] = []

    def nonce(self) -> int:
        return 1000

    def private_call(self) -> None:
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        self.nonces.append(self.nonce())
        time.sleep(0.005)
        self.in_flight -= 1


def test_calls_on_one_client_never_overlap() -> None:
    slow = _SlowExchange()
    client = SerializedExchange(slow)
    threads = [threading.Thread(target=client.private_call) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert slow.max_in_flight == 1
    assert len(set(slow.nonces)) == 8
    assert slow.nonces == sorted(slow.nonces)


class _FakeCcxt:
    """Stands in for a ccxt exchange class. Records the config it was built with."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def nonce(self) -> int:
        return 1000


def test_ccxt_client_is_shared_per_key(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = get_entry("kraken")
    monkeypatch.setattr(private_client.ccxt, entry.ccxt_id, _FakeCcxt)
    monkeypatch.setenv(entry.env_key, "key-1")
    monkeypatch.setenv(entry.env_secret, "secret-1")
    first = ccxt_client(entry)
    assert ccxt_client(entry) is first
    monkeypatch.setenv(entry.env_secret, "secret-2")
    assert ccxt_client(entry) is not first
    assert first.nonce() < first.nonce()  # the shared client never repeats a nonce
