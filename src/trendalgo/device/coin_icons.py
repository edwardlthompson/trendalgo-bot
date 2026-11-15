"""Resolve coin logo PNGs for the Scanner. Prefers a device-owned folder over the retired web tree."""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from trendalgo.icons.aliases import resolve_symbol

_MODULE_REPO = Path(__file__).resolve().parents[3]
_SUFFIXES = (".png", ".PNG", ".jpg", ".jpeg", ".JPG", ".JPEG")


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
        # Curated extras first so new tickers overlay the retired bulk pack.
        folders.append(root / "branding" / "assets" / "coins")
        folders.append(root / "branding" / "assets" / "coins" / "from-retired-web-backup")
        folders.append(root / "examples" / "web" / "public" / "icons" / "coins")
    return tuple(folders)


def coin_icon_dirs() -> tuple[Path, ...]:
    return tuple(folder for folder in _candidates() if folder.is_dir())


def coin_icon_dir() -> Path | None:
    dirs = coin_icon_dirs()
    return dirs[0] if dirs else None


def _names_for(symbol: str) -> tuple[str, ...]:
    base = symbol.strip().upper().split("/")[0]
    if not base:
        return ()
    names = [base]
    alias = resolve_symbol(base)
    if alias != base:
        names.append(alias)
    if base == "XBT":
        names.append("BTC")
    # Preserve order, drop dupes.
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return tuple(out)


@lru_cache(maxsize=256)
def coin_icon_path(symbol: str) -> Path | None:
    """Best matching file for a base symbol (BTC, ETH). Extensions: png, jpg, jpeg."""
    names = _names_for(symbol)
    if not names:
        return None
    for folder in coin_icon_dirs():
        for name in names:
            for suffix in _SUFFIXES:
                candidate = folder / f"{name}{suffix}"
                if candidate.is_file():
                    return candidate
    return None


def clear_coin_icon_cache() -> None:
    coin_icon_path.cache_clear()
