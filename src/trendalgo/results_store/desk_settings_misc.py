"""Settings privacy / data(export+UTC) / updates editors (AV-G-SET7)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device import strings as S
from trendalgo.device.about.update_prefs import load_update_prefs
from trendalgo.device.crash_capture import copy as C
from trendalgo.device.crash_capture.pending_crash import on_save_crashes_changed
from trendalgo.device.crash_capture.save_crashes import get_save_crashes, set_save_crashes
from trendalgo.device.export_prefs import (
    ExportPrefs,
    export_dir,
    load_export_prefs,
    save_export_prefs,
)
from trendalgo.device.profile import SETTINGS_FILE, ProfileError, read_json, write_json
from trendalgo.device.settings_model import (
    settings_from_document,
    settings_to_document,
    validate_settings,
)

__all__ = [
    "apply_data_settings",
    "apply_privacy_settings",
    "check_updates_now",
    "load_data_surface",
    "load_privacy_surface",
    "load_updates_surface",
]


def load_privacy_surface(root: Path) -> dict[str, Any]:
    return {
        "ok": True,
        "save_crashes": get_save_crashes(root),
        "label": C.SAVE_CRASHES,
        "help": C.SAVE_CRASHES_HELP,
        "section": C.PRIVACY_SECTION,
    }


def apply_privacy_settings(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    on = bool(payload.get("save_crashes"))
    set_save_crashes(root, on)
    on_save_crashes_changed(root, on)
    out = load_privacy_surface(root)
    out["ok"] = True
    return out


def load_data_surface(root: Path) -> dict[str, Any]:
    prefs = load_export_prefs(root)
    use_utc = False
    try:
        settings = settings_from_document(read_json(root / SETTINGS_FILE))
        if settings is not None:
            use_utc = bool(settings.use_utc)
    except ProfileError:
        use_utc = False
    resolved = str(export_dir(root))
    return {
        "ok": True,
        "help": S.SETTINGS_DATA_HELP,
        "last_export_dir": prefs.last_export_dir,
        "export_dir": resolved,
        "use_utc": use_utc,
        "use_utc_label": S.SETTINGS_USE_UTC,
        "use_utc_help": S.SETTINGS_USE_UTC_HELP,
        "profile_root": str(root),
    }


def apply_data_settings(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if "last_export_dir" in payload:
        raw = str(payload.get("last_export_dir") or "").strip()
        save_export_prefs(root, ExportPrefs(last_export_dir=raw))
    if "use_utc" in payload:
        path = root / SETTINGS_FILE
        try:
            current = settings_from_document(read_json(path))
        except ProfileError:
            current = None
        if current is None:
            return {
                "ok": False,
                "error": "settings_missing",
                "problems": ["Save Connection (owner ID) before toggling UTC display."],
            }
        updated, problems = validate_settings(
            current.owner_id,
            current.host_url,
            current.theme,
            current.accent,
            current.cert_sha256,
            use_utc=bool(payload.get("use_utc")),
        )
        if updated is None:
            return {"ok": False, "error": "validation", "problems": list(problems)}
        write_json(path, settings_to_document(updated))
    out = load_data_surface(root)
    out["ok"] = True
    return out


def load_updates_surface(root: Path) -> dict[str, Any]:
    from trendalgo import __version__
    from trendalgo.device.about.github_release import changelog_url
    from trendalgo.device.github_feedback.release_repo import load_release_repo

    prefs = load_update_prefs(root)
    repo = load_release_repo() or "edwardbbaity/trendalgo-bot"
    return {
        "ok": True,
        "version": __version__,
        "version_line": S.ABOUT_VERSION.format(version=__version__),
        "check_label": S.ABOUT_CHECK_UPDATES,
        "changelog_label": S.ABOUT_CHANGELOG,
        "changelog_url": changelog_url(repo),
        "support": S.ABOUT_SUPPORT,
        "last_check_at": prefs.last_check_at,
        "last_seen_version": prefs.last_seen_version,
        "dismissed_version": prefs.dismissed_version,
    }


def check_updates_now(root: Path) -> dict[str, Any]:
    from trendalgo import __version__
    from trendalgo.device.about.run_updates import check_for_update

    try:
        result = check_for_update(
            root,
            current_version=__version__,
            interval="launch",
            force=True,
        )
    except Exception as exc:  # noqa: BLE001 — keep Settings alive
        return {
            "ok": False,
            "error": "check_failed",
            "status": "error",
            "message": S.ABOUT_UPDATE_ERROR,
            "detail": str(exc),
        }
    message = S.ABOUT_UPDATE_ERROR
    if result.status == "error":
        message = S.ABOUT_UPDATE_ERROR
    elif result.status == "current" or result.prompt is None:
        message = S.ABOUT_UPDATE_CURRENT
    elif result.status == "donate":
        message = "Donate prompt available"
    elif result.prompt is not None:
        message = S.ABOUT_UPDATE_AVAILABLE.format(version=result.prompt.version)
    return {
        "ok": True,
        "status": result.status,
        "message": message,
        "version": getattr(result.prompt, "version", None) if result.prompt else None,
        "prefs": load_updates_surface(root),
    }
