"""Process-wide order journal under TRENDALGO_DATA_DIR (E2, E3)."""

from __future__ import annotations

import os
import threading
from pathlib import Path

from trendalgo.trading.order_journal import OrderJournal

_JOURNALS: dict[str, OrderJournal] = {}
_JOURNALS_LOCK = threading.Lock()


def default_journal_path() -> Path:
    return Path(os.environ.get("TRENDALGO_DATA_DIR", "data")) / "trading" / "order_journal.db"


def default_journal() -> OrderJournal:
    """One journal per process and path. Callers never open their own connection."""
    path = default_journal_path()
    key = str(path.resolve())
    with _JOURNALS_LOCK:
        if key not in _JOURNALS:
            _JOURNALS[key] = OrderJournal(path)
        return _JOURNALS[key]
