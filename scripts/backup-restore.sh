#!/usr/bin/env bash
# Create or restore TrendAlgo backups (OPS1, OPS2).
# Usage:
#   scripts/backup-restore.sh backup
#   scripts/backup-restore.sh restore --archive path [--apply]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

run_py() {
  if command -v uv >/dev/null 2>&1; then
    uv run python - "$@"
  else
    PYTHONPATH=src python3 - "$@"
  fi
}

cmd="${1:-backup}"
shift || true

case "$cmd" in
  backup)
    run_py <<'PY'
from trendalgo.ops.backup import create_backup, default_paths
data, config, backups = default_paths()
path = create_backup(data_dir=data, config_dir=config, output_dir=backups)
print(f"OK backup={path}")
PY
    ;;
  restore)
    ARCHIVE=""
    APPLY=0
    while [ $# -gt 0 ]; do
      case "$1" in
        --archive) ARCHIVE="$2"; shift 2 ;;
        --apply) APPLY=1; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
      esac
    done
    if [ -z "$ARCHIVE" ]; then
      echo "FAIL --archive required"
      exit 1
    fi
    run_py "$ARCHIVE" "$APPLY" <<'PY'
import sys
from pathlib import Path
from trendalgo.ops.backup import default_paths, restore_backup
archive = Path(sys.argv[1])
apply = bool(int(sys.argv[2]))
data, _, _ = default_paths()
files = restore_backup(archive, dest_root=data.parent, dry_run=not apply)
print(f"OK restore dry_run={not apply} files={len(files)}")
PY
    ;;
  *)
    echo "Usage: backup | restore --archive <path> [--apply]"
    exit 1
    ;;
esac
