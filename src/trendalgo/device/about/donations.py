"""Load and normalize donations.json (quiet Venmo allowlist)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_VENMO_URL = "https://venmo.com/code?user_id=1857304970395648420"
_VENMO = re.compile(r"^https://(?:www\.)?venmo\.com/", re.I)


@dataclass(frozen=True)
class DonationLink:
    label: str
    url: str


@dataclass(frozen=True)
class DonationConfig:
    enabled: bool
    message: str
    links: tuple[DonationLink, ...]


def is_allowed_venmo_url(url: str) -> bool:
    return bool(_VENMO.match(url.strip()))


def primary_donate_url(config: DonationConfig) -> str:
    return config.links[0].url if config.links else DEFAULT_VENMO_URL


def normalize_donations(raw: object) -> DonationConfig:
    if not isinstance(raw, dict):
        return DonationConfig(False, "", ())
    links: list[DonationLink] = []
    for item in raw.get("links") or []:
        if not isinstance(item, dict):
            continue
        label, url = item.get("label"), item.get("url")
        if not isinstance(label, str) or not isinstance(url, str):
            continue
        if "venmo.com" in url.lower() and not is_allowed_venmo_url(url):
            continue
        if url.startswith("[") or label.startswith("["):
            continue
        links.append(DonationLink(label, url))
    enabled = bool(raw.get("enabled")) and bool(links)
    message = raw.get("message") if isinstance(raw.get("message"), str) else ""
    return DonationConfig(enabled, message, tuple(links))


def load_donations(search_roots: list[Path] | None = None) -> DonationConfig:
    roots = search_roots or [Path.cwd()]
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            roots = [*roots, parent]
            break
    for root in roots:
        for name in ("donations.json", "donations.json.example"):
            path = root / name
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            cfg = normalize_donations(data)
            if cfg.links or name.endswith(".example"):
                return cfg
    return DonationConfig(False, "", ())
