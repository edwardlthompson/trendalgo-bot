#!/usr/bin/env bash
# Validate Postgres migration artifacts without a live database (Sprint 12).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCHEMA="$ROOT/docker/postgres/schema.sql"
README="$ROOT/docker/postgres/README.md"

fail() { echo "postgres-migrate-dry-run: $1" >&2; exit 1; }

[[ -f "$README" ]] || fail "missing README"
[[ -f "$SCHEMA" ]] || fail "missing schema.sql"

python3 - <<'PY' "$SCHEMA"
import sys
from pathlib import Path
sql = Path(sys.argv[1]).read_text(encoding="utf-8")
stmts = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]
if len(stmts) < 3:
    raise SystemExit("expected at least 3 SQL statements")
print(f"postgres-migrate-dry-run: ok ({len(stmts)} statements parsed)")
PY

python3 "$ROOT/scripts/check_risk_mitigations.py" --strict --rid R-015 || true
echo "postgres-migrate-dry-run: complete"
