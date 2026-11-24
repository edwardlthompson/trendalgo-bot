"""Global host badge for shell chrome (AV-G-OTH4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device import strings as S
from trendalgo.device.profile import SETTINGS_FILE, ProfileError, read_json
from trendalgo.device.settings_model import settings_from_document
from trendalgo.device.wizard.credentials import OWNER_SECRET_TARGET, MemoryCredentialStore

__all__ = ["load_host_badge_surface"]


def load_host_badge_surface(root: Path) -> dict[str, Any]:
    host_url = ""
    owner_id = ""
    try:
        settings = settings_from_document(read_json(root / SETTINGS_FILE))
    except ProfileError:
        settings = None
    if settings is not None:
        host_url = settings.host_url.strip()
        owner_id = settings.owner_id
    has_secret = _has_owner_secret()
    linked = bool(host_url) and has_secret
    if not linked:
        label = S.BADGE_NO_HOST
        badge = "local"
    else:
        label = S.BADGE_HOST_LINKED
        badge = "linked"
    return {
        "ok": True,
        "linked": linked,
        "host_badge": badge,
        "label": label,
        "host_url": host_url,
        "owner_id": owner_id,
        "has_owner_secret": has_secret,
    }


def _has_owner_secret() -> bool:
    import os

    if os.environ.get("TRENDALGO_WIZARD_MEMORY") == "1":
        return False
    try:
        from trendalgo.device.wizard.credentials import WindowsCredentialStore

        store = WindowsCredentialStore()
        return bool(store.read(OWNER_SECRET_TARGET))
    except Exception:
        # Tests / non-Windows: treat as missing unless Memory store injected.
        _ = MemoryCredentialStore
        return False
