"""Startup crash review + update/donate launch prompt surface (AV-G-STR3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo import __version__ as _ver
from trendalgo.device import strings as S
from trendalgo.device.about.donations import load_donations, primary_donate_url
from trendalgo.device.about.run_updates import decide_launch_prompt
from trendalgo.device.about.update_prefs import mark_update_checked, mark_version_seen
from trendalgo.device.crash_capture import copy as CrashCopy
from trendalgo.device.crash_capture.pending_crash import clear_pending_crash, read_pending_crash


def load_startup_surface(root: Path, *, skip_network: bool = False) -> dict[str, Any]:
    pending = read_pending_crash(root)
    crash = (
        None
        if pending is None
        else {"message": pending.message, "stack": pending.stack, "path": "pending_crash.json"}
    )
    prompt: dict[str, Any] | None = None
    if not skip_network:
        decided = decide_launch_prompt(root, current_version=_ver)
        if decided is not None:
            prompt = {
                "kind": decided.kind,
                "version": decided.version,
                "url": decided.url,
                "changelog": decided.changelog,
                "donate_url": primary_donate_url(load_donations()),
            }
    return {
        "version": _ver,
        "crash": crash,
        "prompt": prompt,
        "copy": {
            "crash_title": CrashCopy.REVIEW_TITLE,
            "crash_body": CrashCopy.REVIEW_BODY,
            "crash_clear": CrashCopy.REVIEW_CLEAR,
            "crash_keep": CrashCopy.REVIEW_KEEP,
            "update_title": S.ABOUT_UPDATE_TITLE,
            "donate_prompt": S.ABOUT_DONATE_PROMPT,
            "donate_accept": S.ABOUT_DONATE_ACCEPT,
            "donate_later": S.ABOUT_DONATE_LATER,
            "update_download": S.ABOUT_UPDATE_DOWNLOAD,
            "update_later": S.ABOUT_UPDATE_LATER,
        },
    }


def ack_startup_prompt(
    root: Path,
    *,
    kind: str,
    version: str = "",
    current_version: str = "",
    dismissed: bool = False,
) -> dict[str, Any]:
    """Persist update/donate ack after Avalonia dialog closes."""
    if kind == "donate":
        mark_version_seen(root, current_version or _ver)
        return {"ok": True, "acked": "donate"}
    if kind == "update":
        from time import time

        if dismissed:
            mark_update_checked(root, time() * 1000, dismissed_version=version or None)
        else:
            mark_update_checked(root, time() * 1000)
        return {"ok": True, "acked": "update", "dismissed": dismissed}
    if kind == "clear_crash":
        clear_pending_crash(root)
        return {"ok": True, "acked": "clear_crash"}
    return {"ok": False, "error": "unknown kind"}
