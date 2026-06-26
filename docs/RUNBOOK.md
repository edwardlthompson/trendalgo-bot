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
| Load test (CM-6) | `bash scripts/load-test-portfolio-sync.sh` | 9+ exchanges sync + trading status, &lt; 30s dry-run |
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

## Multi-venue trading ops (Phase 2, S20)

Registry **v6** · `worldwide_trading_phase: 2` · **9 trading venues** (all portfolio venues):  
`kraken`, `binanceus`, `coinbaseadvanced`, `gemini`, `bitstamp`, `cryptocom`, `binance`, `bybit`, `okx`.

Detail: [`docs/EXCHANGE_ROADMAP.md`](EXCHANGE_ROADMAP.md) · Engine: [`docs/NATIVE_TRADING.md`](NATIVE_TRADING.md)

### Pre-flight checklist

Run before enabling live trading on any new venue or after deploy:

| Step | Check | Expected |
|------|-------|----------|
| 1 | `GET /api/v1/trading/runner/status` | `engine: native`, `exchanges` length **9**, `worldwide_trading_phase: 2` |
| 2 | `GET /api/v1/exchanges/registry` | `version: 6`, nine entries with `trading_enabled: true` |
| 3 | `GET /api/v1/trading/exchanges/control` | One row per trading venue (paused / go-live flags) |
| 4 | `GET /api/v1/trading/adapters` | Nine CCXT adapter ids |
| 5 | `TRENDALGO_MODE` | `dry-run` until founder go-live per venue |
| 6 | Human gate | H-032 approved before **live** on worldwide (`us_restricted`) venues |

Example status probe:

```bash
curl -s http://127.0.0.1:8000/api/v1/trading/runner/status | python -m json.tool
```

### Worldwide ack workflow (live only)

Dry-run works without ack. **Live** orders on `us_restricted` venues (`binance`, `bybit`, `okx`) require **both**:

1. **`[HUMAN]`** H-032 worldwide phase plan approved (see [`docs/HUMAN_BACKLOG.md`](HUMAN_BACKLOG.md))
2. **`[HUMAN]`** Set `WORLDWIDE_TRADING_ACK=1` on the VPS (never commit to git)
3. **`[HUMAN]`** Per-venue go-live: `bash scripts/go-live-gate.sh --approve --exchange binance` (repeat per venue)
4. **`[HUMAN]`** API ack: `POST /api/v1/trading/exchanges/{id}/go-live`
5. **`[HUMAN]`** `GO_LIVE_APPROVED=1` + venue API keys in env + `TRENDALGO_MODE=live`

US retail venues (Kraken, Binance.US, Coinbase Advanced, Gemini, Bitstamp, Crypto.com) skip `WORLDWIDE_TRADING_ACK` but still require steps 3–5 per venue.

Simulated route (dry-run default):

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/trading/exchanges/kraken/route \
  -H 'Content-Type: application/json' \
  -d '{"pair":"BTC/USD","side":"buy","amount":50}'
```

### Daily ops

| Action | API | Notes |
|--------|-----|-------|
| Pause one venue | `PUT /api/v1/trading/exchanges/{id}/pause` `{"paused":true}` | Blocks new orders; portfolio sync continues |
| Resume venue | Same with `"paused":false` | |
| Control snapshot | `GET /api/v1/trading/exchanges/control` | Audit before/after changes |
| Portfolio sync all | `POST /api/v1/portfolio/sync-all` | Uses stagger in prod (`TRENDALGO_SYNC_STAGGER_SEC=15`) |
| Strategy tick (dry-run) | `POST /api/v1/trading/dry-run/tick` | Per-bot; exchange from body |

**Rotation:** Stagger portfolio sync across venues (see Multi-exchange portfolio above). Avoid running full 9-venue sync and live trading bursts on the same API keys simultaneously.

### Arbitrage signals (informational only)

S19 multi-venue detector — **no auto-execution**:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/trading/arbitrage/signals` | Trading-lane spread alerts |
| `GET /api/v1/portfolio/arbitrage` | Portfolio UI lane (same detector) |

Response includes `informational_only: true`, `auto_trade: false`, and a disclaimer. Do not wire alerts to order routing.

### Incidents (N-exchange)

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `WORLDWIDE_TRADING_ACK` error on live route | Missing ack on worldwide venue | Set ack on VPS or stay in dry-run |
| `exchange not enabled for trading` | Registry mismatch or typo | Check `GET /trading/runner/status` |
| One venue paused unexpectedly | Control store | `GET /trading/exchanges/control`; resume if intended |
| Partial portfolio after sync | Missing API keys for venue | `configured: false` in registry response; add env keys |
| Rate limit / slow sync | Too many venues, no stagger | Raise `TRENDALGO_SYNC_STAGGER_SEC`; widen `sync_interval_sec` in registry |
| Wrong pair on worldwide venue | Quote currency mismatch | Use `BTC/USD` — normalizer maps to `BTC/USDT` where needed |

Log user-impacting trading incidents in `DECISION_LOG.md`. Never log API secrets.

## DEX live swaps (S24)

Registry **v4** · `dex_live_phase: 1` · **Base** is the Phase 1 live-trading venue (`trading_enabled: true`).  
Ethereum, Arbitrum, and Solana remain portfolio + dry-run swap only until per-venue go-live.

Detail: [`docs/DEX_ROADMAP.md`](DEX_ROADMAP.md) · Engine: [`docs/adr/0011-dex-venue-plugin-engine.md`](adr/0011-dex-venue-plugin-engine.md)

### Pre-flight checklist

| Step | Check | Expected |
|------|-------|----------|
| 1 | `GET /api/v1/platform/dex/status/full` | `dex_live_phase: 1`, `live_trading_venues` includes `base` |
| 2 | `GET /api/v1/platform/venues/registry` | `version: 4`, Base `trading_enabled: true` |
| 3 | `GET /api/v1/platform/dex/ops-validation` | `ok: true` (CM-6 multi-chain sync) |
| 4 | `TRENDALGO_MODE` | `dry-run` until founder go-live per venue |
| 5 | Human gate | H-036 approved before **live** DEX swaps |

### Live ack workflow

Dry-run swaps work without live ack. **Live** swaps on enabled venues require **all** of:

1. **`[HUMAN]`** H-036 DEX live trading approved ([`docs/HUMAN_BACKLOG.md`](HUMAN_BACKLOG.md))
2. **`[HUMAN]`** Set `DEX_LIVE_TRADING_ACK=1` on the VPS (never commit)
3. **`[HUMAN]`** Set `DEX_SIGNER_KEY` on the VPS only (CM-9 — never API/logs/git)
4. **`[HUMAN]`** `GO_LIVE_APPROVED=1` and per-venue API ack: `POST /api/v1/platform/dex/venues/base/go-live`
5. **`[AGENT]`** Live swap: `POST /api/v1/platform/dex/live` with `slippage_bps` ≤ `DEX_MAX_SLIPPAGE_BPS`

### RPC failover, nonce, slippage

| Control | Env / behavior |
|---------|----------------|
| Primary RPC | `BASE_RPC_URL`, `ETH_RPC_URL`, etc. |
| Failover | `{RPC_ENV}_FALLBACK` (e.g. `BASE_RPC_URL_FALLBACK`) — pinged in order |
| Nonce | Persisted in `data/dex_nonces.json` per venue (auto-increment) |
| Slippage cap | `DEX_MAX_SLIPPAGE_BPS` (default 100); request `slippage_bps` must be ≤ cap |
| Signer audit | Logs use `signer_fingerprint` only — never raw key |

### DEX incidents

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `H-036` / `DEX_LIVE_TRADING_ACK` error | Missing live ack | Set ack on VPS or use `/dex/dry-run` |
| `DEX_SIGNER_KEY required` | Signer not on VPS | Set key on VPS only (CM-9) |
| `go_live_required` | Venue not approved | `POST /dex/venues/{id}/go-live` after H-036 |
| `venue trading not enabled` | Registry gate | Only Base enabled in v4; enable others via registry + ack |
| RPC unreachable | Primary down | Configure `_FALLBACK` URL; check `dex/status/full` → `rpc` |

## Secret Rotation

When credentials leak or a team member with access leaves:

1. **`[HUMAN]`** Revoke compromised tokens/keys in the provider console immediately
2. **`[AGENT]`** Rotate secrets in GitHub Environments and local `.env` (never commit)
3. **`[AGENT]`** Update `.env.example` if variable names changed
4. **`[AUTO]`** Re-run CI with new secrets; confirm deploy health checks pass
5. **`[HUMAN]`** Log incident in `DECISION_LOG.md`; link advisory if CVE-related
