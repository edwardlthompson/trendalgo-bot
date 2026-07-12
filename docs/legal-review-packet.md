# TrendAlgo Bot — Legal Review Packet

Generated: 2026-07-12T03:45:41Z

## Scope for attorney (H-006 / H-023)
- Performance-contingent **software license** (not payment processing)
- User-initiated crypto settlement only; no auto-withdraw
- No KYC; pseudonymous install UUID; no custodial funds

## Included documents

---
## Source: `docs/adr/0009-ai-recommended-strategies.md`

# ADR-0009 — AI-Recommended Strategies (Not Community Marketplace)

- **Status:** Accepted (Sprint 0)
- **Date:** 2026-06-25

## Context

Community strategy imports (G3, IX1, IX2) introduce untrusted code and liability. Product value is operator-curated AI recommendations.

## Decision

1. **Reject** community uploads, custom indicator marketplace, user-imported strategies.
2. **Ship AI5–AI8:** recommender, scanner-to-strategy pipeline, curated library, NL draft with user confirmation.
3. **User confirms all params** before live; backtest-first flow.
4. **Disclaimers:** not financial advice (`docs/AI_STRATEGIES.md`).

## Consequences

Sprint 11 scope; `check-legal-compliance.sh` blocks community import paths; R-012 accepted (AGPL fork).

---
## Source: `docs/AI_STRATEGIES.md`

# AI-Recommended Strategies

> **ADR-0009:** No community marketplace or user-uploaded strategies. Value = LTS Scanner + operator-curated AI recommendations.

## Recommender logic (AI5)

The recommender scores registered templates using:

| Input | Effect |
|-------|--------|
| Active LTS scanner opportunities | Boosts `scanner` and `strong-uptrend-scanner` templates |
| Low drawdown / circuit breaker | Boosts defensive templates (DCA, multi-TF) |
| Small account equity | Boosts DCA |
| Balanced profile | Boosts grid and multi-TF |

Every suggestion includes `requires_backtest: true` and `user_confirms_params: true`.

## Scanner-to-strategy pipeline (AI6)

Qualified pairs from the latest scanner snapshot map to:

- High uniformity + gain → `strong-uptrend-scanner` with tuned `lts_uniform_min`
- High volatility gain → `grid-trading`
- Otherwise → `smart-dca`

## Curated library (AI7)

Versioned presets in `src/trendalgo/ai/curated_library.py` — operator-maintained JSON only. No user uploads.

## Natural-language draft (AI8)

- **Production default:** rule-based parser (`nl_draft.py`)
- **Dev optional:** Ollama when `OLLAMA_HOST` is set
- User must confirm all parameters before deploy

## Growth (G1, G2)

- Referral codes: pseudonymous hash of install UUID (no email/PII)
- Leaderboard: opt-in only; pseudonym `trader-{hash}`; score = net worth snapshot at opt-in

## Boost Mode (B1)

Optional 15% performance license rate (vs 5% standard) for premium curated AI documentation. User-initiated enrollment via API.

## Legal disclaimers

- Software tool only — **not financial advice**
- User responsible for all trades and parameter confirmation
- Backtest before live; dry-run is default until go-live gate
- No auto-withdraw or custodial collection (ADR-0008)

## Rejected (CI enforced)

- Community strategy marketplace (G3)
- Community indicator import (IX1)
- User-uploaded strategy imports (CM1, IX2)
- Hosted multi-tenant trading keys (ADR-0008)

Verification: `bash scripts/check-legal-compliance.sh`

---
## Source: `docs/RISK_REGISTER.md`

# Risk Register — TrendAlgo Bot

> **Catalog:** [`docs/risk-catalog.json`](risk-catalog.json) · **Closed archive:** [`docs/RISK_REGISTER_CLOSED.md`](RISK_REGISTER_CLOSED.md)
> **Verify:** `python scripts/check_risk_mitigations.py [--strict] [--all] [--ongoing]`
> **Post-delivery plan:** [`docs/POST_DELIVERY_PLAN.md`](POST_DELIVERY_PLAN.md)

## Risk Register Zero — achieved (Sprint 12)

| Metric | Status |
|--------|--------|
| Active risks (`status=active`) | **0** |
| Pending critiques | **0** (C-001–C-021 closed) |
| Strict check | `python scripts/check_risk_mitigations.py --strict --all` → PASS |

Closed, eliminated, and accepted risks remain in the catalog for audit trail — they are **not** backlog items.

---

## Ongoing controls (permanent)

These R-IDs stay `ongoing` in the catalog. They require **recurring verification**, not sprint closure.

| R-ID | Risk | Control | Script / artifact | Cadence |
|------|------|---------|-------------------|---------|
| R-003 | Accidental live trading | Dry-run default + go-live gate | `go-live-gate.sh` | Every live enable |
| R-005 | Incorrect license fee | Unit tests + reconciliation | `tests/test_billing/`, `reconcile-fees.sh` | Release |
| R-007 | User non-payment | Grace + license suspension | Billing gate (S10) | Runtime |
| R-008 | Regulatory exposure | Attorney-reviewed TERMS | H-006, H-023, legal packet | Public beta |
| R-009 | Key compromise | Trade+query only, no withdraw | `SECURITY.md`, `check-api-key-policy.sh` | Release |
| R-018 | Scope creep / burnout | Phased BUILD_PLAN, founder gates | `sprint-preflight.sh` | New work |
| R-020 | Backup failure | Encrypted backup + restore test | `backup-restore.sh` | Monthly |
| R-036 | Design system scope creep | File line limits | `check-file-limits.sh` | CI |
| R-039 | CCXT / dependency upstream break | Pinned deps + Dependabot | `uv.lock`, Dependabot | CI |

**Verify all ongoing controls:**

```bash
python scripts/check_risk_mitigations.py --ongoing --strict
```

---

## Accepted risks (documented tradeoffs)

| R-ID | Risk | Note |
|------|------|------|
| R-012 | AGPL fork without billing | Official build + AI value (S11) |
| R-027 | Pseudonymous enforcement limits | License gate on official builds only |
| R-030 | User withdraws before paying | Cannot block exchange; ledger + grace |
| R-038 | VPS single point of failure | Self-hosted tradeoff; OPS1–4 |

No mitigation sprint scheduled — monitor only.

---

## Eliminated risks

| R-ID / topic | Verdict | Enforcement |
|--------------|---------|-------------|
| R-006 | Auto-withdraw / MSB | ADR-0008; `check-legal-compliance.sh` |
| Community untrusted code | **Eliminated** | ADR-0009 |
| Hosted SaaS tenant leak | **Eliminated** | ADR-0008 |
| Institutional auto-collect | **Eliminated** | ADR-0008 |

---

## Closed risks (historical)

41 R-IDs closed at S1–S12. Full list with verification artifacts: [`docs/risk-catalog.json`](risk-catalog.json).

Notable closures:

| Sprint | R-IDs |
|--------|-------|
| S1 | R-001 Kraken quirks |
| S4.5 | R-002, R-013 LTS |
| S5 | R-017, R-022, R-026, R-028 CoinStats parity |
| S10 | R-005–R-011, R-019, R-025, R-029–R-033, R-041 billing/legal |
| S11 | R-023, R-035 AI / leaderboard |
| S12 | R-015 SQLite → Postgres path |

Archive table: [`RISK_REGISTER_CLOSED.md`](RISK_REGISTER_CLOSED.md)

---

## Critiques — all closed

C-001–C-021 are `closed` in the catalog (verified 2026-06-25). Archive: [`RISK_REGISTER_CLOSED.md`](RISK_REGISTER_CLOSED.md) § Critiques closed.

---

## Mandatory gates (human)

| Gate | Blocks | H-ID | Script |
|------|--------|------|--------|
| Legal review | Public beta, license enrollment | H-006, H-023 | `generate-legal-review-packet.sh` |
| Go-live | Live orders | H-010, H-028 | `go-live-gate.sh --approve` |
| CoinStats validation | Cancel subscription | H-017 | `compare-portfolio-parity.sh` |
| Founder preflight | Sprint scope | H-007–H-025 | `founder_gate.py preflight` |

Full automation matrix: [`docs/POST_DELIVERY_PLAN.md`](POST_DELIVERY_PLAN.md) § Human backlog

---

## What to do next

1. **Operate** ongoing controls on the cadence above — no new R-IDs unless regression.
2. **Clear** founder gates per Post-Delivery Phase 1.
3. **Deploy** VPS dry-run before any go-live (Phase 2).
4. **Re-run** `--strict --all` after any catalog change or major release.

---
## Source: `BUILD_PLAN.md`

# TrendAlgo Bot — BUILD_PLAN

> **Detail:** [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
> **Archive:** [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · **Post-delivery:** [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · **Exchange:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md) · **DEX:** [`docs/DEX_ROADMAP.md`](docs/DEX_ROADMAP.md)

## Current sprint: **R-Audit-7 — Post-audit hygiene (2026-07-11)**

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |
**332 tests** · **~87%** coverage · Risk Register Zero ✅

**Agent rule:** `[AGENT]` sequential · after each step → `bash scripts/watch-agent-gates.sh --once --autofix --step none`

**Human gates** (H-030–H-036, go-live, legal): [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) — not duplicated here.

**Audit:** `CODE_REVIEW.md` (ephemeral, gitignored) · 2026-07-11

---

## Program status (summary)

| Program | Sprints | AGENT | Open human gates |
|---------|---------|-------|------------------|
| Core (S0–S12) | Setup → platform, Risk Register Zero | ✅ | H-001–H-029 backlog |
| Exchange | S13–S20 · 9 venues · ADR-0010 | ✅ | **H-032** worldwide live |
| DEX | S21–S24 · Base Phase 1 · ADR-0011 | ✅ | **H-035** scope · **H-036** live |
| Reviews | R-Audit … R-Audit-6 AGENT | ✅ | R-Audit-7 open · PR #7 · H-006 |
Task-level history: [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md). Critique mitigations CM-1–CM-11: closed in [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md).

---

## Open work

### R-Audit-7 — Post-audit hygiene (2026-07-11)

| ID | Task | Owner | Status |
|----|------|-------|--------|
| R-Audit-7.1 | Pin lightweight-charts to 4.x + Dependabot ignore majors; triage PR #10 (F-001) | AGENT | ✅ |
| R-Audit-7.2 | Exclude `.venv*` / site-packages from file-limits; gitignore `.venv*/` (F-004) | AGENT | ✅ |
| R-Audit-7.3 | Sync pyproject + `__init__.py` to 0.4.0; Release Please extra-files (F-003) | AGENT | ✅ |
| R-Audit-7.4 | Sync AGENT_MEMORY / POST_DELIVERY / testing.mdc coverage (F-005) | AGENT | ✅ |
| R-Audit-7.5 | Generate `docs/legal-review-packet.md` for H-006 preflight (F-007) | AGENT | ✅ |
| R-Audit-7.6 | Add root pip Dependabot ecosystem for pyproject/uv.lock (F-006) | AGENT | ✅ |
| R-Audit-7.7 | Gitignore ephemeral `.cursor-*.png` / `mypy-errors.txt`; rename web package (F-008/F-009) | AGENT | ✅ |
| R-Audit-7.8 | Enable Dependency graph + Dependabot alerts (F-002) | HUMAN | 🔲 |
| R-Audit-7.9 | Merge Release Please PR #7 → v0.4.1 tag (F-011 / was R-Audit-6.3) | HUMAN | 🔲 |
| R-Audit-7.10 | Attorney review of legal packet (F-012 / was R-Audit-6.4) | HUMAN | 🔲 |

### Carry-forward (HUMAN)

| Track | Owner | Status |
|-------|-------|--------|
| Founder preflights S0–S12 | HUMAN | 🔲 |
| Legal (H-006, H-023) | HUMAN | 🔲 blocks public beta |
| VPS + secrets (H-004, H-008, H-011) | HUMAN | 🔲 |
| Go-live per venue (H-010, H-028) | HUMAN | 🔲 |
| Exchange live worldwide (H-032) | HUMAN | 🔲 |
| DEX live (H-035, H-036) | HUMAN | 🔲 |
| CI green + v0.4.x tag | AGENT/HUMAN | 🔲 merge PR #7 (R-Audit-7.9) |
| Risk Register Zero | AUTO | ✅ |
| Scope preflights H-013–H-025 | AGENT | ✅ |

Founder gates, VPS, legal, go-live, and recurring controls — full checklist: [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md).

### Maintenance cadence

| Cadence | Owner | Item |
|---------|-------|------|
| Weekly | AUTO | `check_risk_mitigations.py` · CI/CodeQL on `main` · Dependabot triage |
| Monthly | AUTO | portfolio integrity · production cost · backup dry-run (R-020) |
| Pre-live | AUTO/HUMAN | `go-live-gate.sh --check-only` → `--approve` (H-010/H-028) |

Local preview (S13+ UI/API): [`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md) · `scripts/dev-local.ps1`

Founder gate CLI: [`docs/FOUNDER_GATES.md`](docs/FOUNDER_GATES.md) · `python scripts/founder_gate.py status`

---

## Owner labels

| Label | Owner |
|-------|-------|
| `AGENT` | Code, docs, tests |
| `HUMAN` | Credentials, legal, go-live |
| `AUTO` | CI / gate scripts |

**Hard gates (never AUTO):** H-006, H-008, H-010, H-011, H-023, H-028, H-031, H-032, H-036

---

## Archived sprints

Full task lists: [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md).

| Sprint | Closed | Archive |
|--------|--------|---------|
| S27 | 2026-06-29 | TA fleet backtest + v0.4.0 Settings/billing (see COMPLETED_TASKS) |
| S25–S26 | 2026-06-26 | TA cache epic + file-limit gate alignment (see COMPLETED_TASKS) |
| DEX S21–S24 | 2026-06-26 | Plugin engine → dry-run → Base live (see COMPLETED_TASKS) |
| Exchange S13–S20 | 2026-06-26 | Native CCXT → worldwide Phase 2 → ops |
| R-Audit-7 | 🔲 open | Post-audit hygiene · charts pin · version sync |
| R-Audit-6 | 2026-07-11 | Post v0.4.0 CI mypy (AGENT ✅; HUMAN → R-Audit-7.9/7.10) |
| R-Audit-5 | 2026-06-26 | CI axe + offline e2e + KB-013 |
| R-Audit-4 | 2026-06-26 | Doc sync post DEX S21–S24 |
| R-Audit … R-Audit-3 | 2026-06-25 | Post-program doc sync |
| S0–S12 | 2026-06-25 | MVP → platform · Risk Register Zero |
| Post-Delivery | 🔲 open | [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) |

## Checklist for counsel
- [ ] Performance license framing vs MSB / money transmission (PR/US)
- [ ] TERMS.md wording — tool only, not investment advice
- [ ] User-initiated settlement copy — no auto-collect claims
- [ ] Data minimization — no IP/email in consent log
