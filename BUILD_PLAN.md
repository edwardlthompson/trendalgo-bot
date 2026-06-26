# TrendAlgo Bot — BUILD_PLAN

> **Canonical detail:** [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
> **Completed work:** [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · **Post-delivery:** [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · **Exchanges:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md) · **DEX:** [`docs/DEX_ROADMAP.md`](docs/DEX_ROADMAP.md)

## Current sprint: **Post-Delivery / maintenance**

S0–S12, R-Audit, R-Audit-2, R-Audit-3, R-Audit-4, exchange sprints **S13–S20**, and DEX **S21–S24** are complete. **170 tests** · **~86%** coverage.

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |

**Agent rule:** `[AGENT]` Sequential first · after each step → `bash scripts/watch-agent-gates.sh --once --autofix`

**Human gates** (H-030–H-036, go-live, legal): [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) — not duplicated here.

---

## Completed — DEX Plugin Program (S21–S24)

Detail in [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · Roadmap: [`docs/DEX_ROADMAP.md`](docs/DEX_ROADMAP.md)

| Sprint | Exit | Status |
|--------|------|--------|
| **S21** | Venue plugin engine; EVM + Solana wallet read | ✅ |
| **S22** | Uniswap V3 LP, 0x quotes, multi-chain sync | ✅ |
| **S23** | Dry-run swaps (Uniswap V3 + Jupiter) | ✅ |
| **S24** | Live swaps + ops (Base Phase 1) | ✅ AGENT · H-036 open |

### DEX program critique mitigations (CM-8–CM-11)

| ID | Sprint | Task summary | Status |
|----|--------|--------------|--------|
| CM-8 | S21 | Plugin registry; no hardcoded chain logic in API | ✅ |
| CM-9 | S23–S24 | No raw key in code/logs; signer env-only on VPS | ✅ |
| CM-10 | S23 | Dry-run default; live requires H-036 + per-venue ack | ✅ |
| CM-11 | S24 | No `transfer`/withdraw helpers in `dex/runner/` | ✅ |

---

## Completed — Exchange Program (S13–S20)

Detail in [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md).

| Sprint | Exit | Status |
|--------|------|--------|
| **S13** | Registry v1; Kraken refactor; Binance.US portfolio | ✅ |
| **S14** | Generic CCXT portfolio; Tier B US; pair normalizer; stagger stub | ✅ |
| **S15** | Native runner US MVP; Freqtrade removed (CM-1/2/4/7) | ✅ |
| **S16** | All US CEX native trading; billing attribution by exchange | ✅ |
| **S17** | Bitstamp + Crypto.com portfolio; walk-forward; load test | ✅ |
| **S18** | Worldwide Phase 1 trading (binance, bybit, okx); `worldwide_trading_phase: 1` | ✅ AGENT · H-032 open |
| **S19** | Phase 2 (bitstamp/cryptocom trading); multi-venue arbitrage; `worldwide_trading_phase: 2` | ✅ AGENT · H-032 open |
| **S20** | N-exchange ops runbook; CM-6 @ 9 venues; Tier D closed | ✅ AGENT · H-032 open |

**Trading venues (9):** kraken, binanceus, coinbaseadvanced, gemini, bitstamp, cryptocom, binance, bybit, okx

### Exchange program critique mitigations (CM-1–CM-7)

| ID | Sprint | Task summary | Status |
|----|--------|--------------|--------|
| CM-1 | S15 | Native backtest adapter + dry-run runner | ✅ |
| CM-2 | S15–S16 | Strategy runtime contract + template ports | ✅ |
| CM-3 | S17 | Walk-forward on native backtest | ✅ |
| CM-4 | S15 | Remove Freqtrade — port keepers, delete rest | ✅ |
| CM-5 | ongoing | H-030 scope cap; sprint-preflight | 🔲 |
| CM-6 | S14, S17, S20 | Staggered sync + N-exchange load test | ✅ |
| CM-7 | S15 | No `withdraw` in `trading/runner/` | ✅ |

---

## Post-delivery (parallel)

Founder gates, VPS deploy, and recurring controls — full checklist: [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md).

| Track | Owner | Status |
|-------|-------|--------|
| Founder gate preflights S0–S12 | HUMAN | 🔲 |
| Soft gate batch approve | HUMAN | 🔲 |
| Legal (H-006, H-023) | HUMAN | 🔲 blocks public beta |
| VPS + secrets (H-004, H-008, H-011) | HUMAN | 🔲 |
| Go-live (H-010, H-028) | HUMAN | 🔲 per exchange |
| Exchange gates (H-030, H-031, H-032, H-034) | HUMAN | 🔲 see HUMAN_BACKLOG |
| DEX gates (H-035, H-036) | HUMAN | 🔲 see HUMAN_BACKLOG |
| Risk Register Zero | AUTO | ✅ |
| Scope-gate preflights H-013–H-025 | AGENT | ✅ |

---

## Local Preview Protocol (LP)

Run before S13+ commits touching `examples/web/` or `src/trendalgo/api/`.

| Tier | When | Command |
|------|------|---------|
| L1 | Daily / before feature commits | `scripts/dev-local.ps1` or `dev-local.sh` |
| L2 | Sprint sign-off | `scripts/preview-local.ps1` + `python scripts/run-trendalgo-tests.py` |
| L3 | Pre go-live staging | `docker compose --profile full` |

1. ✅ [AGENT] `docs/LOCAL_DEV.md` + `dev-local` / `preview-local` scripts
2. ✅ [AGENT] Docker dev API port aligned to **8000** (Vite proxy)
3. ✅ [AUTO] LP checklist in PR template (S13+ UI/API)
4. ✅ [AGENT] End-of-sprint L2 (S20 close)

---

## Automation summary (S13+)

| Script | Purpose |
|--------|---------|
| `python scripts/founder_gate.py preflight H-030` | Exchange scope artifacts |
| `python scripts/founder_gate.py preflight H-031` | ADR-0010 present |
| `python scripts/founder_gate.py preflight H-032` | Worldwide phase registry |
| `python scripts/founder_gate.py preflight H-034` | LOCAL_DEV + dev scripts |
| `python scripts/founder_gate.py preflight H-035` | DEX program scope (S21–S24 incl. S23 dry-run) |
| `python scripts/founder_gate.py preflight H-036` | DEX live trading (hard) |
| `python scripts/founder_gate.py approve-all-soft` | Batch soft gates |
| `bash scripts/sprint-preflight.sh --sprint N` | Sprint N scope (13+) |
| `scripts/dev-local.ps1` | L1 preview |

---

## Owner labels

| Label | Owner |
|-------|-------|
| `AGENT` | Cursor Agent — code, docs, tests |
| `HUMAN` | Founder — credentials, legal, product decisions |
| `AUTO` | CI / gate scripts |

**Hard gates (never AUTO-approve):** H-006, H-008, H-010, H-011, H-023, H-028, **H-031**, **H-032** · **Non-blocking:** H-002

Commands: [`docs/FOUNDER_GATES.md`](docs/FOUNDER_GATES.md) · `python scripts/founder_gate.py status`

---

## Constraints

| Rule | Detail |
|------|--------|
| Legal (#0) | No KYC · No custodial funds · No MSB · User-initiated license payment only |
| Cost | Production **< $10/mo** (Oracle free → Hetzner ~$5–8) |
| Hosting | **Never** live/production on local PR hardware (ADR-0002) |
| Engine | **Native CCXT runner** (ADR-0010) — Freqtrade removed S15 CM-4 |
| DEX | **Venue plugin engine** (ADR-0011) — S21+; signer env on VPS |
| Monetization | Calculation-only license; user-initiated settlement (ADR-0008) |
| Rejected | Community marketplace, hosted SaaS, Stripe, auto-withdraw, Freqtrade legacy mode |

---

## ADR index

| ADR | Topic |
|-----|-------|
| 0001 | Freqtrade engine (superseded by 0010) |
| **0010** | **Native CCXT engine** |
| **0011** | **DEX venue plugin engine** (S21) |
| 0002 | External VPS hosting |
| 0004 | CoinStats replacement portfolio |
| 0005–0008 | Performance license, legal-safe monetization |
| 0006 | LTS → Opportunity Scanner |
| 0009 | AI strategies only — no community imports |

Full list: [`DECISION_LOG.md`](DECISION_LOG.md) · Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Sprint history

Detailed task lists for S0–S12 and R-Audit: [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md).

| Sprint | Phase | Deliverable | Status |
|--------|-------|-------------|--------|
| 0 | Setup | ADRs, scaffold, founder-gate infra | ✅ |
| 1 | MVP | Freqtrade Kraken dry-run | ✅ |
| 2 | MVP | Risk manager, journal, Telegram | ✅ |
| 3 | MVP | Web UI, PWA, pause-all | ✅ |
| 4 | MVP | VPS deploy path, portfolio seed, webhooks | ✅ |
| 4.5 | v1 core | LTS Opportunity Scanner | ✅ |
| 5 | v1 core | CoinStats-class portfolio + daily P/L | ✅ |
| 6–8 | v1/v2 | Templates, research, multi-exchange | ✅ |
| 10 | Product | Performance license + settlement UX | ✅ |
| 11 | Growth | AI recommender + anonymous referral | ✅ |
| 12 | Platform | On-chain, forager, Postgres path, **Risk Register Zero** | ✅ |
| R-Audit-3 | Review | Doc sync post S18 (README, THREAT_MODEL, KB-009) | ✅ |
| R-Audit-4 | Review | Doc sync post DEX S21–S24 (README, POST_DELIVERY, KB-011) | ✅ |
| R-Audit-2 | Review | Doc sync post exchange program | ✅ |
| R-Audit | Review | README, CORS, KB, archived table | ✅ |
| **S13** | Exchange | Registry, Kraken + Binance.US portfolio | ✅ |
| **S14** | Exchange | Worldwide portfolio + Tier B US | ✅ |
| **S15** | Exchange | Native runner + FT removal | ✅ |
| **S16** | Exchange | All US CEX native trading | ✅ |
| **S17** | Exchange | US hardening (Bitstamp, Crypto.com, CM-3/6) | ✅ |
| **S18** | Exchange | Worldwide Phase 1 (binance, bybit, okx) | ✅ |
| **S19** | Exchange | Phase 2 + arbitrage (bitstamp/cryptocom, multi-venue signals) | ✅ |
| **S20** | Exchange | N-exchange ops hardening | ✅ |
| **S21** | DEX | Venue plugin engine; EVM + Solana wallet read | ✅ |
| **S22** | DEX | Uniswap V3 LP, 0x quotes, multi-chain sync | ✅ |
| **S23** | DEX | Dry-run swaps (Uniswap V3 + Jupiter) | ✅ |
| **S24** | DEX | Live swaps + ops | ✅ AGENT · H-036 open |

---

## Risk & gates (summary)

**Register Zero:** achieved Sprint 12 — 0 active risks in [`docs/risk-catalog.json`](docs/risk-catalog.json).

**Ongoing controls:** R-003 go-live · R-005/R-007 billing · R-008/R-009 legal/keys · R-018 scope · R-020 backup · R-036 file limits · R-039 deps

Full matrix: [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md) · [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md)

| Gate | When | H-ID |
|------|------|------|
| Exchange scope | Before S13 | H-030 |
| Native engine + FT removal | Before S15 | H-031 |
| Worldwide trading | Before S18 live | H-032 |
| Local preview | S13+ commits | H-034 |
| Legal review | Public beta | H-006, H-023 |
| Go-live | Every live enable | H-010, H-028 |
| DEX program scope (incl. S23 dry-run swaps) | Before S21 | H-035 |
| DEX live swap trading | Before S24 live | H-036 |
| RPC endpoints | Before S21 | H-025 |

---

## Ongoing maintenance

### Weekly

- 🔲 [AUTO] `python scripts/check_risk_mitigations.py` (non-strict)
- 🔲 [AUTO] CI + CodeQL green on `main`
- 🔲 [AUTO] VPS health cron + Telegram down-alert *(when deployed)*
- 🔲 [AGENT] Triage Dependabot bumps

### Monthly

- 🔲 [AUTO] `check-portfolio-integrity.sh` → H-026 human review
- 🔲 [AUTO] `check-production-cost.sh` → H-027
- 🔲 [AUTO] `check-risk-mitigations.sh --ongoing`
- 🔲 [AUTO] `backup-restore.sh` dry-run (R-020)

### Pre-live (every enable)

- 🔲 [AUTO] `go-live-gate.sh --check-only`
- 🔲 [HUMAN] `go-live-gate.sh --approve` (H-010 / H-028)

---

## Archived sprints

| Sprint | Closed | Archive |
|--------|--------|---------|
| R-Audit-4 | 2026-06-26 | post DEX program doc sync |
| DEX S24 | 2026-06-26 | Live swaps + ops (Base Phase 1) |
| DEX S23 | 2026-06-26 | Dry-run swaps |
| DEX S22 | 2026-06-26 | Portfolio plugins |
| DEX S21 | 2026-06-26 | Foundation (EVM + Solana wallet read) |
| Post-Delivery | 🔲 open | [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) |
| Exchange S20 | 2026-06-26 | N-exchange ops runbook, CM-6 @ 9 venues, Tier D closed |
| Exchange S19 | 2026-06-26 | Phase 2 trading, multi-venue arbitrage |
| Exchange S18 | 2026-06-26 | Worldwide Phase 1 trading |
| Exchange S17 | 2026-06-25 | Bitstamp/Crypto.com, walk-forward, load test |
| Exchange S16 | 2026-06-25 | US CEX native trading |
| Exchange S15 | 2026-06-25 | Native runner, FT removal |
| Exchange S14 | 2026-06-25 | Generic CCXT, Tier B/C portfolio, stagger |
| Exchange S13 | 2026-06-25 | Registry, binanceus, adapters |
| R-Audit-3 | 2026-06-25 | Post–S18 doc sync, KB-009, R-039 label |
| R-Audit-2 | 2026-06-25 | Post–exchange-doc doc sync, KB-008, PR LP checklist |
| R-Audit | 2026-06-25 | `COMPLETED_TASKS.md` |
| S12 Platform | 2026-06-25 | Risk Register Zero |
| S11 AI & Growth | 2026-06-25 | Recommender, referral |
| S10 License | 2026-06-25 | Billing, settlement |
| S8 Portfolio Adv | 2026-06-25 | Multi-exchange |
| S7 Research | 2026-06-25 | Monte Carlo, export |
| S6 Templates | 2026-06-25 | Multi-bot |
| S5 Portfolio | 2026-06-25 | CoinStats replacement |
| S4.5 Scanner | 2026-06-25 | LTS absorption |
| S4 Deploy | 2026-06-25 | VPS, webhooks |
| S3 Web UI | 2026-06-25 | PWA dashboard |
| S2 Risk | 2026-06-25 | Journal, Telegram |
| S1 Engine | 2026-06-25 | Freqtrade dry-run |
| S0 Init | 2026-06-25 | Scaffold, ADRs |
