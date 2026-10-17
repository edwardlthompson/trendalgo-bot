"""Opt-in local crash queue for the device app. Never auto-sends."""

from trendalgo.device.crash_capture.pending_crash import (
    PendingCrash,
    clear_pending_crash,
    on_save_crashes_changed,
    persist_pending_crash,
    read_pending_crash,
    sanitize_crash_payload,
)

__all__ = [
    "PendingCrash",
    "clear_pending_crash",
    "on_save_crashes_changed",
    "persist_pending_crash",
    "read_pending_crash",
    "sanitize_crash_payload",
]
