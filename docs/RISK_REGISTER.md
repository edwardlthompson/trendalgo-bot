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
