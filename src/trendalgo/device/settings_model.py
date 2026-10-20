"""Device settings: the owner id, an optional host address, and the look. Checked before anything is saved.

Reading is lenient for the look (a bad theme or accent falls back to the default), so a cosmetic
value never blocks saving a plan. The Settings form stays strict.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from trendalgo.device import design_tokens as T
from trendalgo.device.profile import ProfileError

OWNER_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
OWNER_MESSAGE = "Owner ID: use 1 to 64 letters, numbers, dashes, or underscores."
HOST_MESSAGE = "Host address: use https:// and a host name, for example https://host.example:8443."
THEME_CHOICES: tuple[str, ...] = ("system", "light", "dark")
ACCENT_CHOICES: tuple[str, ...] = ("", *T.ACCENT_PRESETS)
THEME_MESSAGE = "Theme: pick follow Windows, light, or dark."
ACCENT_MESSAGE = "Accent color: pick one of the listed colors."
BAD_SETTINGS = "settings.json has a value that is not valid. Move the file aside, then save again."
PIN_MESSAGE = "Certificate pin: paste the host SHA-256 fingerprint (64 hex characters)."


@dataclass(frozen=True)
class Settings:
    owner_id: str
    host_url: str = ""
    cert_sha256: str = ""
    theme: str = "system"
    accent: str = ""
    use_utc: bool = False


def validate_settings(
    owner_text: str,
    host_text: str,
    theme: str = "system",
    accent: str = "",
    cert_pin_text: str = "",
    *,
    use_utc: bool = False,
) -> tuple[Settings | None, list[str]]:
    errors: list[str] = []
    owner = owner_text.strip()
    if not OWNER_ID.fullmatch(owner):
        errors.append(OWNER_MESSAGE)
    host = host_text.strip()
    if host and not _is_https_url(host) and not _is_loopback_http(host):
        errors.append(HOST_MESSAGE)
    pin = _normalize_pin(cert_pin_text)
    if pin is not None and pin is False:
        errors.append(PIN_MESSAGE)
    picked_theme = theme.strip().lower()
    if picked_theme not in THEME_CHOICES:
        errors.append(THEME_MESSAGE)
    picked_accent = accent.strip().lower()
    if picked_accent not in ACCENT_CHOICES:
        errors.append(ACCENT_MESSAGE)
    if errors:
        return None, errors
    pin_value = "" if pin is None else str(pin)
    return Settings(owner, host, pin_value, picked_theme, picked_accent, bool(use_utc)), []


def _is_https_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        _ = parts.port
    except ValueError:
        return False
    return parts.scheme == "https" and bool(parts.hostname)


def _is_loopback_http(url: str) -> bool:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    return parts.scheme == "http" and parts.hostname == "127.0.0.1" and port is not None


def _normalize_pin(text: str) -> str | None | bool:
    """Empty input is allowed. False means invalid."""
    raw = text.strip().replace(":", "").lower()
    if not raw:
        return None
    if len(raw) != 64 or any(ch not in "0123456789abcdef" for ch in raw):
        return False
    return raw


def settings_to_document(settings: Settings) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "owner_id": settings.owner_id,
        "host_url": settings.host_url,
        "theme": settings.theme,
        "accent": settings.accent,
        "use_utc": bool(settings.use_utc),
    }
    if settings.cert_sha256:
        doc["cert_sha256"] = settings.cert_sha256
    return doc


def settings_from_document(document: dict[str, Any] | None) -> Settings | None:
    """The saved settings, or None when nothing is saved yet. Bad owner or host raises ProfileError.

    A missing or unknown theme or accent reads as the default, so older files still load.
    """
    if document is None:
        return None
    theme = _choice(document.get("theme"), THEME_CHOICES, "system")
    accent = _choice(document.get("accent"), ACCENT_CHOICES, "")
    settings, _ = validate_settings(
        str(document.get("owner_id", "")),
        str(document.get("host_url", "")),
        theme,
        accent,
        str(document.get("cert_sha256", "")),
        use_utc=_as_bool(document.get("use_utc"), False),
    )
    if settings is None:
        raise ProfileError(BAD_SETTINGS)
    return settings


def _as_bool(raw: object, default: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _choice(value: object, choices: tuple[str, ...], default: str) -> str:
    text = value.strip().lower() if isinstance(value, str) else ""
    return text if text in choices else default
