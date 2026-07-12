# Post-Delivery Plan — TrendAlgo Bot

> After S0–S12 + Risk Register Zero. **BUILD_PLAN** active board: Post-Delivery Operations.

## Status snapshot (2026-07-11)

| Area | State |
|------|-------|
| Feature sprints | S0–S12 ✅ |
| Exchange program | S13–S20 ✅ AGENT · H-032 open for live worldwide |
| DEX program | S21–S24 ✅ AGENT · H-035/H-036 open for live DEX |
| Risk Register Zero | ✅ 0 active risks; 9 ongoing controls |
| Critiques C-001–C-021 | ✅ all closed in catalog |
| Tests | 332 pass · ~87% `trendalgo` coverage (cov-fail-under=86%) |
| Founder gates H-001–H-036 | 🔲 backlog — preflights mostly runnable |
| Public beta | ❌ blocked on H-006, H-023 |
| Live trading | ❌ blocked on H-010, H-028, H-031, H-032, H-036, secrets |

---

## Phase 1 — Clear founder gates (this week)

Run preflights (Windows: use Python CLI):

```bash
python scripts/founder_gate.py preflight-sprint --sprint 0
python scripts/founder_gate.py preflight-sprint --sprint 1
# … through --sprint 12
python scripts/founder_gate.py status
```

### Batch approve (soft gates only)

After each `preflight` returns **PASS**, one command clears the gate:

```bash
python scripts/founder_gate.py approve H-007
python scripts/founder_gate.py approve-bundle pre-sprint-1   # H-001, H-005, H-007
```

Recommended order:

1. **Pre-Sprint-1 bundle** — H-001, H-005, H-007 (repo + ADR-0001)
2. **Scope gates** — H-013, H-015, H-018, H-019, H-020, H-024, H-025 (after sprint preflight PASS)
3. **Infra checks** — H-009, H-012, H-014, H-016, H-017 (script artifacts)
4. **Secrets** — H-008, H-011 (hard — requires `.env` with real tokens)
5. **Legal** — H-006, H-022, H-023 (hard — attorney; cannot batch approve)
6. **Go-live** — H-010, H-028 (hard — only when deploying live)

---

## Phase 2 — Production path

| Step | Owner | Depends on |
|------|-------|------------|
| Provision VPS (Oracle / Hetzner) | HUMAN | H-004 |
| `setup-secrets.sh` + `.env` | HUMAN | H-008, H-011 |
| Deploy dry-run stack | HUMAN/AGENT | H-004, docker compose |
| Validate portfolio vs CoinStats | HUMAN | H-017, `compare-portfolio-parity.sh` |
| Archive standalone LTS repo | HUMAN | H-014, `lts-parity-check.sh` |
| Attorney TERMS review | HUMAN | H-006, H-023 |
| Enable Dependabot alerts | HUMAN | GitHub settings |
| First live enable | HUMAN | H-010, H-028, `go-live-gate.sh --approve` |

---

## Phase 3 — Ongoing controls (no end date)

These **ongoing risks** in the catalog are **controls**, not open backlog items:

| R-ID | Control | Cadence | Script |
|------|---------|---------|--------|
| R-003 | No accidental live trading | Every go-live | `go-live-gate.sh` |
| R-005 | Fee calculation accuracy | Each release | `tests/test_billing/` |
| R-007 | Non-payment / grace | Runtime | License gate (S10) |
| R-008 | Regulatory compliance | Public beta + releases | Legal packet, TERMS |
| R-009 | API key policy | Each release | `check-api-key-policy.sh` |
| R-018 | Scope discipline | New work only | `sprint-preflight.sh` |
| R-020 | Backup / restore | Monthly | `backup-restore.sh` |
| R-036 | File size limits | CI | `check-file-limits.sh` |
| R-039 | CCXT / deps pin | CI + Dependabot | `uv.lock`, Dependabot |

**Accepted (documented, no action):** R-012 AGPL fork · R-027 pseudonym limits · R-030 withdraw-before-pay · R-038 VPS SPOF

**Verify ongoing controls:**

```bash
python scripts/check_risk_mitigations.py --ongoing --strict
```

---

## Human backlog — automation matrix

| H-ID | Item | AUTO preflight | Can AUTO-approve? | Human action required |
|------|------|----------------|-------------------|------------------------|
| H-001 | Repo name / origin / README | ✅ `preflight H-001` | ✅ soft | Review README + remote URL |
| H-002 | Pick Cursor mode | ✅ doc exists | ✅ optional | Non-blocking |
| H-003 | Branch protection | ✅ script present | ✅ soft | Run `setup-github-repo.sh` once |
| H-004 | VPS hosting choice | ✅ eligibility script | ✅ soft | **Provision** Oracle/Hetzner account |
| H-005 | Founder defaults | ✅ defaults file | ✅ soft | Override only if changing defaults |
| H-006 | Attorney + ADR-0008 | ⚠️ legal packet exists | ❌ **hard** | **Attorney consult** |
| H-007 | ADR-0001 / S1 scope | ✅ ADR + bootstrap | ✅ soft | Read ADR-0001 |
| H-008 | Telegram token | ⚠️ `.env` exists | ❌ **hard** | **Create bot, paste secrets** |
| H-009 | Playwright smoke | ✅ config exists | ✅ soft | CI runs tests |
| H-010 | Live trading approval | ✅ go-live script | ❌ **hard** | **Explicit live enable** |
| H-011 | Kraken read-only keys | ⚠️ `.env` exists | ❌ **hard** | **Create API keys** |
| H-012 | Production cost check | ✅ script | ✅ soft | Review monthly output |
| H-013 | LTS absorption scope | ✅ sprint-preflight S4 | ✅ soft | Read ADR-0006 |
| H-014 | Archive LTS repo | ✅ parity script | ⚠️ soft | **GitHub archive action** |
| H-015 | S5 scope / UI bar | ✅ sprint-preflight S5 | ✅ soft | Product sign-off |
| H-016 | Notification hour | ✅ smoke script | ⚠️ soft | **Pick hour on VPS** |
| H-017 | CoinStats parity | ✅ parity script | ⚠️ soft | **Manual compare + cancel sub** |
| H-018 | S6 scope | ✅ sprint-preflight S6 | ✅ soft | Read scope |
| H-019 | S7 scope | ✅ sprint-preflight S7 | ✅ soft | Read scope |
| H-020 | S8 scope | ✅ sprint-preflight S8 | ✅ soft | Read scope |
| H-021 | Second exchange / futures | ❌ product decision | ❌ hard | **Choose exchange + timeline** |
| H-022 | License ADR attorney | ⚠️ legal docs exist | ❌ **hard** | **Attorney on license model** |
| H-023 | TERMS sign-off | ⚠️ TERMS.md exists | ❌ **hard** | **Attorney approval** |
| H-024 | S11 scope (no marketplace) | ✅ sprint-preflight S11 | ✅ soft | Confirm ADR-0009 |
| H-025 | S12 on-chain provider | ✅ sprint-preflight S12 | ⚠️ soft | **Approve provider or stay dry-run** |
| H-026 | Portfolio integrity review | ✅ script report | ⚠️ AUTO runs; human **reviews** | Read monthly report |
| H-027 | VPS cost ≤ $10 | ✅ script | ⚠️ AUTO runs; human **confirms** | Confirm invoice |
| H-028 | Repeat go-live | ✅ go-live script | ❌ **hard** | **Each live enable** |
| H-029 | Default license rate | ✅ defaults | ✅ fully AUTO | Already in founder defaults |
| H-030 | Exchange program scope | ✅ roadmap + BUILD_PLAN | ✅ soft | Read EXCHANGE_ROADMAP |
| H-031 | ADR-0010 + FT removal | ⚠️ ADR exists | ❌ **hard** | **Explicit FT removal consent** |
| H-032 | Worldwide bot trading | ⚠️ roadmap § Tier D | ❌ **hard** | **Approve phase plan** |
| H-034 | Local preview sign-off | ✅ LOCAL_DEV + scripts | ✅ soft | **Run L1 preview** |

### Already fully automated (no backlog row)

H-003 · H-009 · H-012 · H-029 · H-005 (defaults applied)

### Batch soft approve

```bash
python scripts/founder_gate.py approve-all-soft --dry-run
python scripts/founder_gate.py approve-all-soft
```

### Recommended AGENT follow-ups (optional)

1. Add GitHub Action: weekly `founder_gate.py preflight-sprint` + artifact report
2. Enable Dependabot via `gh api` if repo admin token available

---

## Risk register — nothing left to “close”

All R-001–R-041 are terminal in `risk-catalog.json`. Remaining work is:

1. **Operate** ongoing controls (table above)
2. **Clear** human gates for deploy/beta
3. **Monitor** accepted risks (fork, VPS SPOF, withdraw-before-pay)

Do **not** re-open closed risks unless a regression is found; log new issues as KB entries or a new R-ID in a future maintenance sprint.

---

## Success criteria — Post-Delivery done

- [ ] All soft founder gates `approved` in `.cursor/founder-gates.json`
- [ ] VPS running dry-run bot + API + PWA
- [ ] H-017 parity validated; CoinStats cancelled
- [ ] H-006 + H-023 cleared for public beta
- [ ] Dependabot alerts enabled
- [ ] First `go-live-gate.sh --approve` recorded (if live trading desired)
- [ ] Monthly cron: backup, cost, portfolio integrity, ongoing risk check
