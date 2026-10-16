"""Fleet backtest progress file. The fleet job runs in a worker, so the window polls JSON in the profile."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Protocol

from trendalgo.device.profile import ProfileError, read_json, write_json

PROGRESS_FILE = "fleet_backtest_progress.json"
WRITE_EVERY_S = 0.5


class FleetSnapshotSource(Protocol):
    def snapshot(self) -> dict[str, Any] | None: ...


class FleetProgressReporter:
    """Copies fleet runner snapshots into the profile folder while a job runs."""

    def __init__(
        self,
        root: Path,
        source: FleetSnapshotSource,
        interval_s: float = WRITE_EVERY_S,
    ) -> None:
        self._path = root / PROGRESS_FILE
        self._source = source
        self._interval = interval_s
        self._halt = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="fleet-progress", daemon=True)

    def start(self) -> None:
        self._write()
        self._thread.start()

    def stop(self) -> None:
        self._halt.set()
        if self._thread.is_alive():
            self._thread.join(timeout=self._interval * 4 + 1.0)
        self._write()

    def _loop(self) -> None:
        while not self._halt.wait(self._interval):
            self._write()

    def _write(self) -> None:
        snap = self._source.snapshot()
        if snap is None:
            return
        try:
            write_json(self._path, {"snapshot": snap})
        except OSError:
            pass


def write_snapshot(root: Path, snapshot: dict[str, Any]) -> None:
    try:
        write_json(root / PROGRESS_FILE, {"snapshot": snapshot})
    except OSError:
        pass


def read_progress(root: Path) -> dict[str, Any] | None:
    try:
        payload = read_json(root / PROGRESS_FILE)
    except ProfileError:
        return None
    if not payload:
        return None
    snap = payload.get("snapshot")
    return snap if isinstance(snap, dict) else None


def clear_progress(root: Path) -> None:
    (root / PROGRESS_FILE).unlink(missing_ok=True)
