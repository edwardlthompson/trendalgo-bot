"""Resolve config JSON shipped in the repo or PyInstaller datas."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def config_candidates(rel: str, *, env_var: str, default: Path) -> list[Path]:
    """Env override, frozen ``_MEIPASS`` / exe dir, then checkout + cwd."""
    out: list[Path] = []
    env = os.environ.get(env_var)
    if env:
        out.append(Path(env))
    meipass = getattr(sys, "_MEIPASS", None)
    if isinstance(meipass, str):
        out.append(Path(meipass) / rel)
    if getattr(sys, "frozen", False):
        out.append(Path(sys.executable).resolve().parent / rel)
    out.append(default)
    out.append(Path.cwd() / rel)
    return out


def first_existing(candidates: list[Path], *, label: str) -> Path:
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"{label} not found (tried {[str(p) for p in candidates]})")
