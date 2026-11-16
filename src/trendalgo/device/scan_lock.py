"""Cross-process lock: one Opportunity scan_job at a time per profile lane."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.lock import ProfileBusyError, ProfileLock

LOCK_FILE = "opportunity_scan.lock"
BUSY_MESSAGE = (
    "An Opportunity scan is already running on this profile. "
    "Wait for it to finish, or cancel it first."
)


class ScanBusyError(RuntimeError):
    """Another process or worker already holds the Opportunity scan lock."""


def _lock_name(lane: str = "crypto") -> str:
    key = (lane or "crypto").strip().lower()
    if key in {"", "crypto"}:
        return LOCK_FILE
    return f"opportunity_scan_{key}.lock"


def opportunity_scan_lock(root: Path, lane: str = "crypto") -> ProfileLock:
    return ProfileLock(root / _lock_name(lane))


def try_acquire_scan_lock(root: Path, lane: str = "crypto") -> ProfileLock:
    """Acquire or raise ScanBusyError."""
    lock = opportunity_scan_lock(root, lane)
    try:
        lock.acquire()
    except ProfileBusyError as exc:
        raise ScanBusyError(BUSY_MESSAGE) from exc
    return lock


def scan_lock_held(root: Path, lane: str = "crypto") -> bool:
    """True if another holder already owns this lane's Opportunity scan lock."""
    probe = opportunity_scan_lock(root, lane)
    try:
        probe.acquire()
    except ProfileBusyError:
        return True
    probe.release()
    return False
