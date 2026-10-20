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
_EVENT_LIMIT = 300


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
        # Full recent ring so the UI can catch up if a poll missed a write.
        latest = get_scan_progress().snapshot(after=0, limit=_EVENT_LIMIT)
        events = list(latest.get("events") or [])
        last_seq = int(latest.get("last_seq") or 0)
        message = str(events[-1]["message"]) if events else ""
        slim = [{"seq": int(e["seq"]), "message": str(e.get("message") or "")} for e in events]
        try:
            write_json(
                self._path,
                {
                    "state": latest["state"],
                    "message": message,
                    "last_seq": last_seq,
                    "events": slim,
                },
            )
        except OSError:
            pass  # a locked or full disk must not stop the scan; the window keeps the last good copy


def consume_progress_events(
    progress: dict[str, Any] | None, after_seq: int
) -> tuple[list[str], int]:
    """New log lines with ``seq > after_seq``, plus the highest seq seen (cursor)."""
    if not progress:
        return [], after_seq
    events = progress.get("events")
    if not isinstance(events, list):
        return [], after_seq
    lines: list[str] = []
    cursor = int(after_seq)
    for raw in events:
        if not isinstance(raw, dict):
            continue
        try:
            seq = int(raw.get("seq") or 0)
        except (TypeError, ValueError):
            continue
        if seq <= cursor:
            continue
        message = str(raw.get("message") or "").strip()
        if message:
            lines.append(message)
        cursor = max(cursor, seq)
    return lines, cursor


def read_progress(root: Path) -> dict[str, Any] | None:
    """The last copy the worker wrote. None when there is none yet or it cannot be read this time."""
    try:
        return read_json(root / PROGRESS_FILE)
    except ProfileError:
        return None  # the worker may be mid-write; the next poll reads it again


def clear_progress(root: Path) -> None:
    (root / PROGRESS_FILE).unlink(missing_ok=True)
