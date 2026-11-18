"""Persist last PNG export directory across share dialogs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from trendalgo.device.profile import EXPORTS_DIR, read_json, write_json

PREFS_FILE = "export_prefs.json"


@dataclass
class ExportPrefs:
    last_export_dir: str = ""


def prefs_path(root: Path) -> Path:
    return root / PREFS_FILE


def load_export_prefs(root: Path) -> ExportPrefs:
    raw = read_json(prefs_path(root))
    if not isinstance(raw, dict):
        return ExportPrefs()
    return ExportPrefs(last_export_dir=str(raw.get("last_export_dir") or "").strip())


def save_export_prefs(root: Path, prefs: ExportPrefs) -> None:
    write_json(prefs_path(root), asdict(prefs))


def export_dir(root: Path) -> Path:
    """Last used export directory if it still exists; else ``{root}/exports``."""
    prefs = load_export_prefs(root)
    candidate = Path(prefs.last_export_dir) if prefs.last_export_dir else None
    if candidate is not None and candidate.is_dir():
        return candidate
    fallback = root / EXPORTS_DIR
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def suggested_png_path(root: Path, filename: str) -> Path:
    safe = Path(filename).name or "export.png"
    if not safe.lower().endswith(".png"):
        safe = f"{safe}.png"
    return export_dir(root) / safe


def remember_export_dir(root: Path, chosen: Path | str) -> None:
    """Remember the parent folder of a successful save (never crashes)."""
    try:
        parent = Path(chosen).expanduser().resolve().parent
    except OSError:
        return
    if not parent.is_dir():
        return
    save_export_prefs(root, ExportPrefs(last_export_dir=str(parent)))
