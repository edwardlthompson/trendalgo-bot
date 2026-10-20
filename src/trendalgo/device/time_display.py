"""Format datetimes for the device UI using the PC local zone or UTC."""

from __future__ import annotations

from datetime import UTC, datetime, tzinfo
from pathlib import Path

from trendalgo.device.profile import read_json
from trendalgo.device.settings_model import settings_from_document


def local_tz() -> tzinfo:
    """OS local timezone from the PC clock."""
    tz = datetime.now().astimezone().tzinfo
    return tz if tz is not None else UTC


def ensure_aware(dt: datetime) -> datetime:
    """Treat naive values as UTC (storage convention)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def format_display_time(dt: datetime | str | None, *, use_utc: bool = False) -> str:
    """User-facing timestamp: local by default, or UTC when toggled."""
    parsed = _parse(dt)
    if parsed is None:
        return ""
    aware = ensure_aware(parsed)
    if use_utc:
        shown = aware.astimezone(UTC)
        return shown.strftime("%Y-%m-%d %H:%M UTC")
    shown = aware.astimezone(local_tz())
    return shown.strftime("%Y-%m-%d %H:%M")


def load_use_utc(root: Path) -> bool:
    """Read the Settings use_utc flag (default False = local)."""
    try:
        settings = settings_from_document(read_json(root / "settings.json"))
    except Exception:  # noqa: BLE001 — display must not fail on bad prefs
        return False
    return bool(settings.use_utc) if settings is not None else False


def _parse(raw: datetime | str | None) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    text = str(raw).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
