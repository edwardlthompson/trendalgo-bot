# HUMAN Backlog — TrendAlgo Bot

> **Single source of truth** for open founder actions. Same markers as [`BUILD_PLAN.md`](../BUILD_PLAN.md).
>
> **Archived ✅ gates** → [`COMPLETED_TASKS.md`](../COMPLETED_TASKS.md). Do not leave ✅ rows here.
>
> **Template upgrade v1.10.0 (human):** H-BA-9/12/19/20 + R-BA.H1 archived 2026-10-16. Skills map: [`docs/SKILLS_RECIPES.md`](SKILLS_RECIPES.md) · MCP: [`docs/MCP_RECIPES.md`](MCP_RECIPES.md).

## Markers (same as BUILD_PLAN)

| Marker | Meaning |
|--------|---------|
| 🔲 | Open — you still need to act (or formally `approve`) |
| ✅ | Done — archive to COMPLETED_TASKS, remove from this file |
| ❌ | Blocked |
## Why scripts do not auto-✅

| Kind | What the script does | Why still 🔲 until you act |
|------|----------------------|----------------------------|
| Soft scope | Checks docs/ADR exist | Needs `approve --note` (or was archived after approve) |
| Soft + real action | Proves a helper exists | Needs VPS / GitHub / hour pick / etc. |
| Hard | Packet or go-live script | Never AUTO — secrets, attorney, live trading |
| Monthly | Report / cost check | Recurring |

```bash
python scripts/founder_gate.py status
python scripts/founder_gate.py preflight H-00N
python scripts/founder_gate.py approve H-00N --note "why you approve"

```

**Hard gates (never AUTO-approve):** H-006, H-008, H-010, H-011, H-023, H-028, **H-031**, **H-032**, **H-036**

---

## Open gates (🔲 only)

### Dashboard / calendar

| ID | Task | Owner | Status |
|----|------|-------|--------|
| PF-H1 | Optional: mint CoinMarketCal and/or Coindar API keys (Calendar wizard) | `[HUMAN]` | 🔲 |
### DEX

| ID | Task | Owner | Status |
|----|------|-------|--------|
| H-036 | Approve **live** DEX swap trading (hard) | `[HUMAN]` | 🔲 |
### Exchange

| ID | Task | Owner | Status |
|----|------|-------|--------|
| H-032 | Approve worldwide bot trading phases (hard) | `[HUMAN]` | 🔲 |
### Post-delivery / ops

| ID | Task | Owner | Status |
|----|------|-------|--------|
| H-003 | Branch protection setup (`setup-github-repo.sh`) | `[HUMAN]` | 🔲 |
| H-004 | Provision VPS (Oracle / Hetzner) — script only checks DEPLOYMENT.md | `[HUMAN]` | 🔲 |
| H-006 | Attorney + ADR-0008 (hard) | `[HUMAN]` | 🔲 |
| H-007 | Approve ADR-0001 / S1 — blocked until `validate-bootstrap --quick` passes | `[HUMAN]` | 🔲 |
| H-008 | Telegram token in `.env` (hard) | `[HUMAN]` | 🔲 |
| H-010 | Explicit live-trading approval (hard) | `[HUMAN]` | 🔲 |
| H-011 | Kraken read-only keys in `.env` (hard) | `[HUMAN]` | 🔲 |
| H-017 | CoinStats parity compare + cancel sub — **deferred** (parity gaps; revisit later) | `[HUMAN]` | 🔲 |
| H-022 | License ADR attorney (hard) | `[HUMAN]` | 🔲 |
| H-023 | TERMS sign-off (hard) | `[HUMAN]` | 🔲 |
### Recurring (never one-shot ✅)

| ID | Cadence | Task | Owner | Status |
|----|---------|------|-------|--------|
| H-026 | Monthly | Review portfolio integrity report | `[HUMAN]` | 🔲 |
| H-027 | Monthly | Confirm VPS cost ≤ $10 | `[HUMAN]` | 🔲 |
| H-028 | Every go-live | Explicit go-live approve (hard) | `[HUMAN]` | 🔲 |
---

## AUTO-only (not open backlog)

| ID | Note |
|----|------|
| H-009 | Playwright smoke (CI) — scheduled / CI path |
| H-012 | Production cost script — monthly helper |
| H-029 | Default license rate (founder defaults) |
---

## Reference

[`docs/FOUNDER_GATES.md`](FOUNDER_GATES.md) · [`docs/POST_DELIVERY_PLAN.md`](POST_DELIVERY_PLAN.md) · state: `.cursor/founder-gates.json`
