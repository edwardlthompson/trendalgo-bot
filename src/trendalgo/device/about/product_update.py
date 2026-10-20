"""Pure product-update rules: daily check, version compare, asset pick, donate nudge."""

from __future__ import annotations

import re
from dataclasses import dataclass

MS_DAY = 86_400_000
DEFAULT_ASSET_PREFIX = "TrendAlgo"


@dataclass(frozen=True)
class NamedAsset:
    name: str
    url: str


def should_check_daily(last_check_at: float | None, now: float) -> bool:
    if last_check_at is None:
        return True
    return now - last_check_at >= MS_DAY


def compare_versions(current: str, latest: str) -> int:
    def parse(v: str) -> list[int]:
        return [int(part) if part.isdigit() else 0 for part in v.split(".")]

    a, b = parse(current), parse(latest)
    for i in range(3):
        diff = (a[i] if i < len(a) else 0) - (b[i] if i < len(b) else 0)
        if diff:
            return diff
    return 0


def is_newer_version(current: str, latest: str) -> bool:
    return compare_versions(current, latest) < 0


def parse_asset_version(name: str, *, kind: str, prefix: str) -> str | None:
    src, stem = name.strip(), prefix.strip()
    if not src or not stem:
        return None
    esc = re.escape(stem)
    pattern = (
        rf"{esc}-(\d+\.\d+\.\d+)" if kind == "exe" else rf"{esc.lower()}-(\d+\.\d+\.\d+)-foss\.apk"
    )
    match = re.search(pattern, src, re.IGNORECASE)
    return match.group(1) if match else None


def select_product_asset(
    assets: list[NamedAsset],
    *,
    kind: str,
    prefix: str,
) -> tuple[str, str] | None:
    for asset in assets:
        version = parse_asset_version(asset.name, kind=kind, prefix=prefix)
        if version and asset.url:
            return version, asset.url
    return None


def should_nudge_donate(last_seen_version: str | None, current_version: str) -> bool:
    if not current_version.strip():
        return False
    if not (last_seen_version or "").strip():
        return False
    return last_seen_version.strip() != current_version.strip()


def should_prompt_update(
    current_version: str,
    latest_version: str | None,
    dismissed_version: str | None,
) -> bool:
    if not latest_version:
        return False
    if not is_newer_version(current_version, latest_version):
        return False
    if dismissed_version and dismissed_version == latest_version:
        return False
    return True


def preview_release_notes(body: str, *, limit: int = 800) -> str:
    """Plain-text preview of GitHub release notes for the update dialog."""
    text = body.replace("\r\n", "\n").strip()
    if not text:
        return ""
    # Light markdown noise strip (headers, bold/italic markers, links).
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) <= limit:
        return text
    cut = text[: max(0, limit - 1)].rstrip()
    return f"{cut}…"
