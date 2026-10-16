"""Fill TRENDALGO_* env when the frozen exe is started without the VBS launcher."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_device_env() -> None:
    """Discover repo.root / coin icons when Desktop shortcuts were bypassed."""
    if (
        os.environ.get("TRENDALGO_COIN_ICONS", "").strip()
        and os.environ.get("TRENDALGO_ROOT", "").strip()
    ):
        return
    roots = _discover_repo_roots()
    for root in roots:
        if not os.environ.get("TRENDALGO_ROOT", "").strip():
            os.environ["TRENDALGO_ROOT"] = str(root)
        icons = root / "branding" / "assets" / "coins" / "from-retired-web-backup"
        if not icons.is_dir():
            icons = root / "branding" / "assets" / "coins"
        if icons.is_dir() and not os.environ.get("TRENDALGO_COIN_ICONS", "").strip():
            os.environ["TRENDALGO_COIN_ICONS"] = str(icons)
        if os.environ.get("TRENDALGO_COIN_ICONS", "").strip():
            break
    try:
        from trendalgo.device.coin_icons import clear_coin_icon_cache

        clear_coin_icon_cache()
    except Exception:
        pass


def _discover_repo_roots() -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen or not resolved.is_dir():
            return
        seen.add(resolved)
        found.append(resolved)

    exe = Path(sys.executable).resolve()
    for parent in (exe.parent, *exe.parents):
        marker = parent / "repo.root"
        if marker.is_file():
            text = marker.read_text(encoding="utf-8").strip()
            if text:
                add(Path(text))
        if (parent / "branding" / "assets" / "coins").is_dir():
            add(parent)
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "TrendAlgo" / "repo.root"
    if local.is_file():
        text = local.read_text(encoding="utf-8").strip()
        if text:
            add(Path(text))
    return found
