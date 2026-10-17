"""At-most-one pending crash record (process session + optional profile file)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trendalgo.device.crash_capture.sanitize import sanitize_report_text
from trendalgo.device.crash_capture.save_crashes import get_save_crashes
from trendalgo.device.profile import ProfileError, read_json, write_json

PENDING_FILE = "pending_crash.json"

_session: dict[str, str] | None = None


@dataclass(frozen=True)
class PendingCrash:
    message: str
    stack: str


def pending_path(root: Path) -> Path:
    return root / PENDING_FILE


def sanitize_crash_payload(raw: dict[str, Any]) -> PendingCrash:
    return PendingCrash(
        message=sanitize_report_text(str(raw.get("message") or "")),
        stack=sanitize_report_text(str(raw.get("stack") or ""), stack=True),
    )


def persist_pending_crash(
    root: Path,
    record: PendingCrash | dict[str, Any],
    *,
    save_local: bool | None = None,
) -> bool:
    global _session
    try:
        payload = record if isinstance(record, PendingCrash) else sanitize_crash_payload(record)
        payload = sanitize_crash_payload({"message": payload.message, "stack": payload.stack})
        doc = {"message": payload.message, "stack": payload.stack}
        _session = doc
        keep = get_save_crashes(root) if save_local is None else save_local
        if keep:
            write_json(pending_path(root), doc)
        else:
            _remove_local(root)
        return True
    except (OSError, ProfileError, TypeError, ValueError):
        return False


def read_pending_crash(root: Path) -> PendingCrash | None:
    global _session
    try:
        if _session is not None:
            return sanitize_crash_payload(_session)
        raw = read_json(pending_path(root))
        if not isinstance(raw, dict):
            return None
        if not isinstance(raw.get("message"), str) or not isinstance(raw.get("stack"), str):
            return None
        return sanitize_crash_payload(raw)
    except (OSError, ProfileError, TypeError, ValueError):
        return None


def clear_pending_crash(root: Path) -> None:
    global _session
    _session = None
    _remove_local(root)


def on_save_crashes_changed(root: Path, on: bool) -> None:
    if not on:
        clear_pending_crash(root)


def _remove_local(root: Path) -> None:
    path = pending_path(root)
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass


def reset_session_for_tests() -> None:
    """Clear in-process session state (tests only)."""
    global _session
    _session = None
