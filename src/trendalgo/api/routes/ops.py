from typing import Any

from fastapi import APIRouter, Request

from trendalgo.ops.backup import create_backup, default_paths, restore_backup
from trendalgo.ops.health import composite_health
from trendalgo.ops.version_check import check_github_release

router = APIRouter()


@router.get("/ops/health")
def ops_health(request: Request) -> dict[str, Any]:
    api_base = str(request.base_url).rstrip("/")
    return composite_health(f"{api_base}/api/v1/health")


@router.post("/ops/backup")
def ops_backup() -> dict[str, str]:
    data, config, backups = default_paths()
    archive = create_backup(data_dir=data, config_dir=config, output_dir=backups)
    return {"archive": str(archive)}


@router.post("/ops/restore")
def ops_restore(dry_run: bool = True, archive_path: str = "") -> dict[str, Any]:
    if not archive_path:
        return {"ok": False, "reason": "archive_path required"}
    from pathlib import Path

    data, config, _ = default_paths()
    root = data.parent
    members = restore_backup(Path(archive_path), dest_root=root, dry_run=dry_run)
    return {"ok": True, "dry_run": dry_run, "files": members}


@router.get("/ops/version")
def ops_version() -> dict[str, str | bool]:
    return check_github_release()
