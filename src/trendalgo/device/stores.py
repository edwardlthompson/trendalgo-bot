"""Read-only access to the device's stored data. A missing file gives an empty result and is not created."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from trendalgo.bots.orchestrator import BotOrchestrator
from trendalgo.device.portfolio_model import PortfolioOverview, load_overview
from trendalgo.risk.journal import TradeJournal
from trendalgo.scanner.snapshot import QualifiedSnapshot
from trendalgo.scanner.store import ScannerStore


class StoreReadError(RuntimeError):
    """A stored database exists but cannot be read."""


def _unreadable(path: Path) -> str:
    return f"{path.name} cannot be read. Move it aside, then reload this page."


def read_snapshot(path: Path) -> QualifiedSnapshot | None:
    if not path.is_file():
        return None
    try:
        return ScannerStore(path).latest_successful_snapshot()
    except (sqlite3.Error, ValueError) as exc:
        raise StoreReadError(_unreadable(path)) from exc


def read_bots(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        return BotOrchestrator(path).list_bots()
    except sqlite3.Error as exc:
        raise StoreReadError(_unreadable(path)) from exc


def read_trades(path: Path, limit: int = 50) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        return TradeJournal(path).list_trades(limit)
    except sqlite3.Error as exc:
        raise StoreReadError(_unreadable(path)) from exc


def read_portfolio(path: Path | None, *, as_of_date: str | None = None) -> PortfolioOverview | None:
    """Latest portfolio overview, or None when the file is missing or empty. Never creates the file."""
    if path is None or not path.is_file():
        return None
    try:
        return load_overview(path, as_of_date=as_of_date)
    except (sqlite3.Error, FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        raise StoreReadError(_unreadable(path)) from exc
