"""Scan progress file (D-02). The scan runs in a worker process, so the window reads its progress from a
small JSON file in the profile folder. The worker rewrites that file about twice a second."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from trendalgo.device.profile import ProfileError, read_json, write_json
from trendalgo.scanner.progress import get_scan_progress

PROGRESS_FILE = "scan_progress.json"
WRITE_EVERY_S = 0.5


class ProgressReporter:
    """Copies the worker's scan progress into the profile folder while a scan runs."""

    def __init__(self, root: Path, interval_s: float = WRITE_EVERY_S) -> None:
        self._path = root / PROGRESS_FILE
        self._interval = interval_s
        self._halt = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="scan-progress", daemon=True)

    def start(self) -> None:
        self._write()
        self._thread.start()

    def stop(self) -> None:
        """Stop the copy loop, then write the final state."""
        self._halt.set()
        if self._thread.is_alive():
            self._thread.join(timeout=self._interval * 4 + 1.0)
        self._write()

    def _loop(self) -> None:
        while not self._halt.wait(self._interval):
            self._write()

    def _write(self) -> None:
        latest = get_scan_progress().snapshot(after=0, limit=1)
        events = latest["events"]
        message = str(events[-1]["message"]) if events else ""
        try:
            write_json(self._path, {"state": latest["state"], "message": message})
        except OSError:
            pass  # a locked or full disk must not stop the scan; the window keeps the last good copy


def read_progress(root: Path) -> dict[str, Any] | None:
    """The last copy the worker wrote. None when there is none yet or it cannot be read this time."""
    try:
        return read_json(root / PROGRESS_FILE)
    except ProfileError:
        return None  # the worker may be mid-write; the next poll reads it again


def clear_progress(root: Path) -> None:
    (root / PROGRESS_FILE).unlink(missing_ok=True)
