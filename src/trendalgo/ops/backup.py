"""Automated backup + restore helpers (OPS1, OPS2)."""

from __future__ import annotations

import hashlib
import json
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def create_backup(
    *,
    data_dir: Path,
    config_dir: Path,
    output_dir: Path,
) -> Path:
    """Tar config + SQLite DBs with manifest checksums."""
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"trendalgo-backup-{_utc_stamp()}.tar.gz"
    manifest: dict[str, Any] = {"files": [], "created_at": _utc_stamp()}

    paths: list[Path] = []
    for root in (data_dir, config_dir):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".db", ".json"}:
                paths.append(path)

    with tarfile.open(archive, "w:gz") as tar:
        for path in paths:
            arcname = path.as_posix()
            tar.add(path, arcname=arcname)
            manifest["files"].append({"path": arcname, "sha256": _sha256(path)})

    manifest_path = output_dir / f"{archive.stem}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return archive


def restore_backup(archive: Path, *, dest_root: Path, dry_run: bool = False) -> list[str]:
    """Extract archive into dest_root; dry_run lists members only."""
    restored: list[str] = []
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            if member.isfile():
                restored.append(member.name)
                if not dry_run:
                    tar.extract(member, path=dest_root)
    return restored


def default_paths() -> tuple[Path, Path, Path]:
    root = Path(os.environ.get("TRENDALGO_ROOT", ".")).resolve()
    data = Path(os.environ.get("TRENDALGO_DATA_DIR", root / "data"))
    config = Path(os.environ.get("TRENDALGO_CONFIG_DIR", root / "config"))
    backups = Path(os.environ.get("TRENDALGO_BACKUP_DIR", root / "data" / "backups"))
    return data, config, backups
