"""One shared ccxt client per exchange and key, with serialized calls and monotonic nonces (E8).

Kraken rejects a private call whose nonce is not higher than the last one it saw for the key.
Calls on one client run one at a time, and the nonce never repeats or goes backwards inside
this process. One process must own each key. A second process on the same key can still race
the nonce; the orphan check in trading/reconcile.py is there to catch that.
"""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from typing import Any

import ccxt

from trendalgo.exchanges.registry import ExchangeEntry
from trendalgo.exchanges.secrets import EnvSecretStore, protect_logs


class MonotonicNonce:
    """Nonce source that never repeats or goes backwards, even when the clock does."""

    def __init__(self, source: Callable[[], Any]) -> None:
        self._source = source
        self._last = 0
        self._lock = threading.Lock()

    def __call__(self) -> int:
        with self._lock:
            value = max(int(self._source()), self._last + 1)
            self._last = value
            return value


class SerializedExchange:
    """Wraps one ccxt exchange. Every call runs under one lock, so private calls never overlap."""

    def __init__(self, exchange: Any) -> None:
        self._exchange = exchange
        self._lock = threading.RLock()
        exchange.nonce = MonotonicNonce(exchange.nonce)

    def guard(self) -> Any:
        """Hold the key's lock across several calls, such as a reconcile followed by an order."""
        return self._lock

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._exchange, name)
        if not callable(attr):
            return attr

        def locked(*args: Any, **kwargs: Any) -> Any:
            with self._lock:
                return attr(*args, **kwargs)

        return locked


_CLIENTS: dict[tuple[str, type, str], SerializedExchange] = {}
_CLIENTS_LOCK = threading.Lock()


def ccxt_client(entry: ExchangeEntry) -> SerializedExchange:
    """The shared client for this exchange and key. Built once per process, then reused."""
    exchange_class = getattr(ccxt, entry.ccxt_id, None)
    if exchange_class is None:
        raise ValueError(f"ccxt has no exchange class: {entry.ccxt_id}")
    store = EnvSecretStore()
    protect_logs(entry.env_key, entry.env_secret)
    api_key = store.get(entry.env_key) or ""
    secret = store.get(entry.env_secret) or ""
    digest = hashlib.sha256(f"{api_key}\0{secret}".encode()).hexdigest()
    cache_key = (entry.id, exchange_class, digest)
    with _CLIENTS_LOCK:
        if cache_key not in _CLIENTS:
            options: dict[str, Any] = {"enableRateLimit": True}
            if entry.id == "kraken":
                options["options"] = {"adjustForTimeDifference": True}
            config = {"apiKey": api_key, "secret": secret, **options}
            _CLIENTS[cache_key] = SerializedExchange(exchange_class(config))
        return _CLIENTS[cache_key]
