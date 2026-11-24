"""Shared results.db + IPC for Avalonia shell ↔ Python Research Engine (ADR-0021)."""

from __future__ import annotations

from trendalgo.results_store.ipc import PROTOCOL_VERSION, IpcHandshake, handshake_payload
from trendalgo.results_store.schema import RESULTS_DB, SCHEMA_VERSION
from trendalgo.results_store.store import ResultsStore

__all__ = [
    "IpcHandshake",
    "PROTOCOL_VERSION",
    "RESULTS_DB",
    "SCHEMA_VERSION",
    "ResultsStore",
    "handshake_payload",
]
