# Runbook

> Operational guide for deploy, rollback, and incident response.

## Health Checks

For services and APIs, expose:

| Endpoint | Purpose | Expected |
|----------|---------|----------|
| `/health` | Liveness | `200` when process is up |
| `/ready` | Readiness | `200` when dependencies are reachable |

Static PWAs and CLIs may skip HTTP endpoints; document stack-specific checks instead.

## Structured Logging

- JSON or key-value format in production
- Include correlation/request ID per request
- **Never** log passwords, tokens, or PII without explicit consent
- Log levels: `ERROR` for user-visible failures, `WARN` for recoverable, `INFO` for lifecycle events

## Deploy

1. `[AUTO]` CI green on `main`
2. `[HUMAN]` Approve release (Milestone Gates in `BUILD_PLAN.md`)
3. `[AUTO]` Tag and publish via GitHub Release workflow
4. `[HUMAN]` Verify deployment on target platform

## Rollback

1. Revert to previous release tag or artifact
2. Confirm health checks pass
3. Log incident in `DECISION_LOG.md` if user-impacting

## Common Failures

| Symptom | Check | Fix |
|---------|-------|-----|
| CI failing on lint | Local `pre-commit run --all-files` | Fix and push |
| Dependabot alert | `docs/SECURITY_TRIAGE.md` | Merge bump PR |
| State lost after upgrade | Migration tests | Fix schema migration |

## Backup & Restore

| Target | RPO | RTO | Procedure |
|--------|-----|-----|-----------|
| User data | _Define_ | _Define_ | _Document per stack_ |
| Repository | N/A (git) | Immediate | `git clone` |

## SLOs (`[HUMAN]` defines)

| Service | SLI | Target |
|---------|-----|--------|
| _Example: API availability_ | Uptime | _99.9%_ |
| _Example: page load_ | p95 latency | _< 2s_ |

## Escalation

1. Check `BUILD_PLAN.md` Ongoing Maintenance
2. Review `docs/SECURITY_TRIAGE.md` for security issues
3. Contact maintainers in `.github/CODEOWNERS`

## Go-live (H-010 / H-028)

1. `[AUTO]` `bash scripts/go-live-gate.sh --check-only`
2. `[HUMAN]` Exchange IP whitelist + position caps in each venue UI
3. `[HUMAN]` `bash scripts/go-live-gate.sh --approve --exchange kraken` (per venue; logs to `data/audit/go-live.jsonl`)
4. `[HUMAN]` Enable live only via `config/bot/live.example.json` template after step 3

Dry-run is always default. Never enable live trading without founder gate approval per exchange.

## Multi-exchange portfolio (native engine)

| Check | Command | Expected |
|-------|---------|----------|
| Registry venues | `GET /api/v1/exchanges/registry` | 9+ portfolio venues (v4+) |
| Staggered sync | `TRENDALGO_SYNC_STAGGER_SEC=15` (prod) | Rate-limit friendly |
| Load test (CM-6) | `bash scripts/load-test-portfolio-sync.sh` | 6+ exchanges, &lt; 30s dry-run |
| Parity slice | `bash scripts/compare-portfolio-parity.sh` | Multi-exchange PASS |
| Cost gate | `bash scripts/check-production-cost.sh` | Load test + budget |

**Production sync:** Portfolio scheduler uses `exchanges/scheduler.py` with stagger. On VPS, keep default 15s stagger between venues. For local dev / CI, set `TRENDALGO_SYNC_STAGGER_SEC=0`.

**Incidents:** If sync exceeds 30s with zero stagger, check CCXT rate limits and reduce `sync_interval_sec` in `config/exchanges.registry.json`.

## Native research (CM-3)

Walk-forward on the native backtest path:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/research/walk-forward \
  -H 'Content-Type: application/json' \
  -d '{"strategy":"grid-trading","pair":"BTC/USD","use_native":true}'
```

Response includes `"engine": "native"` and fold-level train/test PnL.

## Worldwide trading (Phase 1, S18)

Tier C venues (`binance`, `bybit`, `okx`) are enabled for native dry-run/live after H-032 approval.

| Guard | Env / API |
|-------|-----------|
| US-restricted ack | `WORLDWIDE_TRADING_ACK=1` before **live** on worldwide venues |
| Per-venue go-live | `POST /api/v1/trading/exchanges/{id}/go-live` |
| Pair quotes | Auto-normalized (`BTC/USD` → `BTC/USDT` on Binance/Bybit/OKX) |

Check status: `GET /api/v1/trading/runner/status` → `worldwide_trading_phase`, `worldwide_exchanges`.

## Secret Rotation

When credentials leak or a team member with access leaves:

1. **`[HUMAN]`** Revoke compromised tokens/keys in the provider console immediately
2. **`[AGENT]`** Rotate secrets in GitHub Environments and local `.env` (never commit)
3. **`[AGENT]`** Update `.env.example` if variable names changed
4. **`[AUTO]`** Re-run CI with new secrets; confirm deploy health checks pass
5. **`[HUMAN]`** Log incident in `DECISION_LOG.md`; link advisory if CVE-related
