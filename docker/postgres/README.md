# PostgreSQL migration path (Sprint 12)

SQLite remains the MVP default per ADR-0001. This directory documents and ships the **PostgreSQL / TimescaleDB cutover path** when single-node SQLite is insufficient (R-015, C-014).

## When to migrate

- Portfolio snapshot volume exceeds comfortable SQLite write rates on your VPS
- You need concurrent API readers during heavy scanner or billing jobs
- You plan **horizontal scaling** (multiple bot instances sharing one DB)

## Components

| Artifact | Purpose |
|----------|---------|
| `schema.sql` | Mirror of core portfolio tables |
| `scripts/postgres-migrate-dry-run.sh` | CI-safe validation (no live DB required) |
| `src/trendalgo/db/postgres_adapter.py` | Dual-write adapter (`TRENDALGO_POSTGRES_DUAL_WRITE=1`) |

## Environment

```bash
export TRENDALGO_POSTGRES_DSN="postgresql://trendalgo:secret@localhost:5432/trendalgo"
export TRENDALGO_POSTGRES_DUAL_WRITE=1   # optional; off by default
```

## Dry-run migration (local / CI)

```bash
bash scripts/postgres-migrate-dry-run.sh
```

Or via API: `POST /api/v1/platform/postgres/migrate-dry-run`

## Live cutover (human-gated)

1. Provision Postgres 16+ (Hetzner, self-hosted, or managed FOSS-friendly provider).
2. Apply `schema.sql` with `psql` or your migration tool.
3. Enable dual-write; verify mirrored rows match SQLite snapshots.
4. Flip read path to Postgres in a maintenance window (future sprint — not required for S12 MVP).
5. Keep SQLite as local cache / backup export source until burn-in completes.

## TimescaleDB (optional)

When `timescaledb` extension is available:

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
SELECT create_hypertable('portfolio_snapshots', 'captured_at', if_not_exists => TRUE);
```

## Horizontal scaling note

Multiple self-hosted bot instances should share **one** Postgres writer and use read replicas or connection pooling (PgBouncer). See `docs/ARCHITECTURE.md` § Horizontal scaling.

## Verification

- Risk R-015 verification: this README + `schema.sql` + dry-run script
- API: `GET /api/v1/platform/postgres/status`
