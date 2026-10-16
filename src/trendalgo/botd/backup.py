"""Snapshot and restore of host SQLite files (H5). A restore checks integrity before it replaces anything."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterable
from contextlib import closing
from pathlib import Path

SIDECAR_SUFFIXES = ("-wal", "-shm")


class BackupError(RuntimeError):
    """A snapshot failed its integrity check, or a copy failed, so nothing was replaced."""


def integrity_ok(path: Path) -> bool:
    """True when path is a SQLite file that passes PRAGMA integrity_check. Never creates a file."""
    if not path.is_file():
        return False
    try:
        with closing(sqlite3.connect(path)) as conn:
            row = conn.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError:
        return False
    return row is not None and row[0] == "ok"


def _copy(src: Path, target: Path) -> None:
    """Online backup API: a consistent copy even while the host is writing."""
    try:
        with closing(sqlite3.connect(src)) as live, closing(sqlite3.connect(target)) as copy:
            live.backup(copy)
    except sqlite3.Error as exc:
        target.unlink(missing_ok=True)
        raise BackupError(f"copy of {src.name} failed: {exc}") from exc


def snapshot(sources: Iterable[Path], dest_dir: Path, *, stamp: str) -> list[Path]:
    """Copy each existing host file into dest_dir as <name>-<stamp>.db. Missing files are skipped."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for src in sources:
        if not src.is_file():
            continue
        target = dest_dir / f"{src.stem}-{stamp}{src.suffix}"
        _copy(src, target)
        if not integrity_ok(target):
            target.unlink(missing_ok=True)
            raise BackupError(f"snapshot of {src.name} failed its integrity check")
        written.append(target)
    return written


def restore(snapshot_path: Path, target: Path) -> None:
    """Replace target with a verified snapshot. Run with the host stopped.

    The copy is verified before the swap, and the swap is one atomic rename. The target's -wal and
    -shm sidecars are removed first, so SQLite cannot replay frames from the old database.
    """
    if not integrity_ok(snapshot_path):
        raise BackupError(f"snapshot {snapshot_path.name} failed its integrity check")
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(target.name + ".restore")
    staged.unlink(missing_ok=True)
    _copy(snapshot_path, staged)
    if not integrity_ok(staged):
        staged.unlink(missing_ok=True)
        raise BackupError(f"restored copy of {snapshot_path.name} failed its integrity check")
    for suffix in SIDECAR_SUFFIXES:
        target.with_name(target.name + suffix).unlink(missing_ok=True)
    os.replace(staged, target)
