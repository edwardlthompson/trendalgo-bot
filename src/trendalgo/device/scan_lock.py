"""Cross-process lock: only one Opportunity scan_job at a time per profile."""

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


def opportunity_scan_lock(root: Path) -> ProfileLock:
    return ProfileLock(root / LOCK_FILE)


def try_acquire_scan_lock(root: Path) -> ProfileLock:
    """Acquire or raise ScanBusyError."""
    lock = opportunity_scan_lock(root)
    try:
        lock.acquire()
    except ProfileBusyError as exc:
        raise ScanBusyError(BUSY_MESSAGE) from exc
    return lock


def scan_lock_held(root: Path) -> bool:
    """True if another holder already owns the Opportunity scan lock."""
    probe = opportunity_scan_lock(root)
    try:
        probe.acquire()
    except ProfileBusyError:
        return True
    probe.release()
    return False
