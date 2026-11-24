"""Settings → Connection: owner / host / cert pin (AV-G-SET4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.profile import SETTINGS_FILE, ProfileError, read_json, write_json
from trendalgo.device.settings_model import (
    settings_from_document,
    settings_to_document,
    validate_settings,
)

__all__ = ["apply_connection_settings", "load_connection_surface"]


def load_connection_surface(root: Path) -> dict[str, Any]:
    path = root / SETTINGS_FILE
    try:
        settings = settings_from_document(read_json(path))
    except ProfileError as exc:
        return {
            "ok": False,
            "error": "bad_settings",
            "problems": [str(exc)],
            "owner_id": "",
            "host_url": "",
            "cert_sha256": "",
            "first_run": True,
            "help": (
                "Owner ID, optional HTTPS host, optional SHA-256 cert pin. "
                "VPS bot host stays headless."
            ),
        }
    if settings is None:
        return {
            "ok": True,
            "owner_id": "",
            "host_url": "",
            "cert_sha256": "",
            "first_run": True,
            "help": (
                "First run — set an Owner ID (letters, numbers, dash, underscore). "
                "Host is optional HTTPS; cert pin is optional 64-hex fingerprint."
            ),
        }
    return {
        "ok": True,
        "owner_id": settings.owner_id,
        "host_url": settings.host_url,
        "cert_sha256": settings.cert_sha256,
        "first_run": False,
        "help": (
            "Owner ID, optional HTTPS host, optional SHA-256 cert pin. VPS bot host stays headless."
        ),
    }


def apply_connection_settings(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path = root / SETTINGS_FILE
    theme = "system"
    accent = ""
    use_utc = False
    try:
        current = settings_from_document(read_json(path))
    except ProfileError:
        current = None
    if current is not None:
        theme = current.theme
        accent = current.accent
        use_utc = current.use_utc

    settings, problems = validate_settings(
        str(payload.get("owner_id", "")),
        str(payload.get("host_url", "")),
        theme,
        accent,
        str(payload.get("cert_sha256", "")),
        use_utc=use_utc,
    )
    if settings is None:
        return {"ok": False, "error": "validation", "problems": list(problems)}
    write_json(path, settings_to_document(settings))
    return {
        "ok": True,
        "owner_id": settings.owner_id,
        "host_url": settings.host_url,
        "cert_sha256": settings.cert_sha256,
        "first_run": False,
    }
