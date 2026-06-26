# TrendAlgo Bot — BUILD_PLAN

> **Canonical detail:** [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
> **Completed work:** [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · **Post-delivery:** [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · **Exchanges:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md)

## Current sprint: **Exchange Program S19**

S0–S12, R-Audit, R-Audit-2, R-Audit-3, and exchange sprints **S13–S18** (AGENT) are complete. **130 tests** · **~86%** coverage.

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |

**Agent rule:** `[AGENT]` Sequential first · after each step → `bash scripts/watch-agent-gates.sh --once --autofix`

**Human gates** (H-030, H-031, H-032, H-034, go-live, legal): [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) — not duplicated here.

---

## Active — Exchange Program (S19–S20)

> **Vision:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md) · **Engine:** ADR-0010 native CCXT · **Trading doc:** [`docs/NATIVE_TRADING.md`](docs/NATIVE_TRADING.md)

**Rule:** Max one exchange-program sprint active (CM-5). Each sprint exit requires **LP L1 minimum**; **L2** at close.

### Sprint 19 — Worldwide Phase 2 + arbitrage (informational)

**Exit:** Phase 2 worldwide venues on native runner; multi-venue arbitrage detector (informational only).

**Blocks:** H-032 (worldwide phase plan — see HUMAN_BACKLOG)

1. 🔲 [AGENT] Phase 2 worldwide venues — registry `worldwide_trading_phase: 2` + `trading_enabled`
2. 🔲 [AGENT] Multi-venue arbitrage detector (informational; no auto-execution)
3. 🔲 [AGENT] Tests + API surface for arbitrage signals
4. 🔲 [AGENT] LP L2 at sprint close

### Sprint 20 — N-exchange ops hardening

**Exit:** Production runbook for N-exchange ops; load/parity gates at scale.

1. 🔲 [AGENT] Runbook: multi-venue trading ops, worldwide ack workflow
2. 🔲 [AGENT] CM-6 scale validation (9+ venues sync + trading status)
3. 🔲 [AGENT] Docs sync — EXCHANGE_ROADMAP Tier D closed, BUILD_PLAN archived
4. 🔲 [AGENT] LP L2 at sprint close

### Critique mitigations (exchange program)

| ID | Sprint | Task summary | Status |
|----|--------|--------------|--------|
| CM-1 | S15 | Native backtest adapter + dry-run runner | ✅ |
| CM-2 | S15–S16 | Strategy runtime contract + template ports | ✅ |
| CM-3 | S17 | Walk-forward on native backtest | ✅ |
| CM-4 | S15 | Remove Freqtrade — port keepers, delete rest | ✅ |
| CM-5 | ongoing | H-030 scope cap; sprint-preflight | 🔲 |
| CM-6 | S14, S17 | Staggered sync + load test | ✅ |
| CM-7 | S15 | No `withdraw` in `trading/runner/` | ✅ |

---

## Completed — Exchange Program (S13–S18)

Detail in [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md).

| Sprint | Exit | Status |
|--------|------|--------|
| **S13** | Registry v1; Kraken refactor; Binance.US portfolio | ✅ |
| **S14** | Generic CCXT portfolio; Tier B US; pair normalizer; stagger stub | ✅ |
| **S15** | Native runner US MVP; Freqtrade removed (CM-1/2/4/7) | ✅ |
| **S16** | All US CEX native trading; billing attribution by exchange | ✅ |
| **S17** | Bitstamp + Crypto.com portfolio; walk-forward; load test | ✅ |
| **S18** | Worldwide Phase 1 trading (binance, bybit, okx); `worldwide_trading_phase: 1` | ✅ AGENT · H-032 open |

**Trading venues (7):** kraken, binanceus, coinbaseadvanced, gemini, binance, bybit, okx  
**Portfolio-only (2):** bitstamp, cryptocom

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
4. 🔲 [AGENT] End-of-sprint L2 (S19 close)

---

## Automation summary (S13+)

| Script | Purpose |
|--------|---------|
| `python scripts/founder_gate.py preflight H-030` | Exchange scope artifacts |
| `python scripts/founder_gate.py preflight H-031` | ADR-0010 present |
| `python scripts/founder_gate.py preflight H-032` | Worldwide phase registry |
| `python scripts/founder_gate.py preflight H-034` | LOCAL_DEV + dev scripts |
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
| Monetization | Calculation-only license; user-initiated settlement (ADR-0008) |
| Rejected | Community marketplace, hosted SaaS, Stripe, auto-withdraw, Freqtrade legacy mode |

---

## ADR index

| ADR | Topic |
|-----|-------|
| 0001 | Freqtrade engine (superseded by 0010) |
| **0010** | **Native CCXT engine** |
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
| R-Audit-2 | Review | Doc sync post exchange program | ✅ |
| R-Audit | Review | README, CORS, KB, archived table | ✅ |
| **S13** | Exchange | Registry, Kraken + Binance.US portfolio | ✅ |
| **S14** | Exchange | Worldwide portfolio + Tier B US | ✅ |
| **S15** | Exchange | Native runner + FT removal | ✅ |
| **S16** | Exchange | All US CEX native trading | ✅ |
| **S17** | Exchange | US hardening (Bitstamp, Crypto.com, CM-3/6) | ✅ |
| **S18** | Exchange | Worldwide Phase 1 (binance, bybit, okx) | ✅ |
| **S19–S20** | Exchange | Phase 2 + arbitrage + N-exchange ops | 🔲 |

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
| Post-Delivery | 🔲 open | [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) |
| Exchange S19–S20 | 🔲 planned | this section (active above) |
| Exchange S18 | 2026-06-25 | Worldwide Phase 1 trading |
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
