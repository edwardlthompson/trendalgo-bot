"""Resolve coin logo PNGs for the Scanner. Prefers a device-owned folder over the retired web tree."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

_MODULE_REPO = Path(__file__).resolve().parents[3]


def _candidates() -> tuple[Path, ...]:
    folders: list[Path] = []
    env = os.environ.get("TRENDALGO_COIN_ICONS", "").strip()
    if env:
        folders.append(Path(env))
    root_env = os.environ.get("TRENDALGO_ROOT", "").strip()
    roots: list[Path] = []
    if root_env:
        roots.append(Path(root_env))
    roots.append(_MODULE_REPO)
    bundled = getattr(sys, "_MEIPASS", None)
    if isinstance(bundled, str):
        roots.append(Path(bundled))
    for root in roots:
        folders.append(root / "branding" / "assets" / "coins" / "from-retired-web-backup")
        folders.append(root / "branding" / "assets" / "coins")
        folders.append(root / "examples" / "web" / "public" / "icons" / "coins")
    return tuple(folders)


def coin_icon_dir() -> Path | None:
    for folder in _candidates():
        if folder.is_dir():
            return folder
    return None


@lru_cache(maxsize=256)
def coin_icon_path(symbol: str) -> Path | None:
    """Best matching file for a base symbol (BTC, ETH). Extensions: png, jpg, jpeg."""
    folder = coin_icon_dir()
    if folder is None:
        return None
    base = symbol.strip().upper().split("/")[0]
    if not base:
        return None
    for name in (base, "BTC" if base == "XBT" else base):
        for suffix in (".png", ".PNG", ".jpg", ".jpeg", ".JPG", ".JPEG"):
            candidate = folder / f"{name}{suffix}"
            if candidate.is_file():
                return candidate
    return None


def clear_coin_icon_cache() -> None:
    coin_icon_path.cache_clear()
