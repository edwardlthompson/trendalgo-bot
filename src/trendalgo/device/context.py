"""Device context: the profile folder and the paths every page reads from."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trendalgo.device.profile import LOCK_FILE, PLAN_FILE, SETTINGS_FILE, db_paths, profile_dir


@dataclass(frozen=True)
class DeviceContext:
    root: Path
    databases: dict[str, Path]
    settings_path: Path
    plan_path: Path
    lock_path: Path
    # Existing portfolio.db when found (shared or profile). Never created on open.
    portfolio_path: Path | None = None
    # Names of databases outside the profile folder (the API's files). They are read, never switched to WAL.
    shared: frozenset[str] = frozenset()


def open_context(root: Path | None = None) -> DeviceContext:
    """Create the profile folder if needed and return the paths. Opens no database."""
    from trendalgo.device.portfolio_model import portfolio_db_path

    base = profile_dir() if root is None else root
    base.mkdir(parents=True, exist_ok=True)
    databases = db_paths(base)
    return DeviceContext(
        root=base,
        databases=databases,
        settings_path=base / SETTINGS_FILE,
        plan_path=base / PLAN_FILE,
        lock_path=base / LOCK_FILE,
        portfolio_path=portfolio_db_path(base),
        shared=frozenset(name for name, path in databases.items() if not _inside(path, base)),
    )


def _inside(path: Path, folder: Path) -> bool:
    return path.resolve().is_relative_to(folder.resolve())
