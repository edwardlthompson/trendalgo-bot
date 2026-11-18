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
| Hard | Packet or go-live script | Never AUTO — secrets, legal residual-risk / Tier B counsel, live trading |
| Monthly | Report / cost check | Recurring |

```bash
python scripts/founder_gate.py status
python scripts/founder_gate.py preflight H-00N
python scripts/founder_gate.py approve H-00N --note "why you approve"

```

**Hard gates (never AUTO-approve):** H-006, **H-006b**, H-008, H-010, H-011, H-023, H-028, **H-031**, **H-032**, **H-036**

Tier A legal (H-006 / H-022 / H-023) archived ✅ 2026-11-15. Tier B (**H-006b**): counsel/clinic before non-owner billing — see [`docs/legal-desk/when-to-get-counsel.md`](legal-desk/when-to-get-counsel.md).

---

## Open gates (🔲 only) — complete in this order

Canonical ordered pack also on [`BUILD_PLAN.md`](../BUILD_PLAN.md) **Human work**. Path: **legal → ops → secrets → live → expand**.

| # | ID | Task | Kind | Status |
|---|----|------|------|--------|
| 1 | H-006b | Tier B: counsel/clinic before non-owner billing | Hard · legal Tier B | 🔲 |
| 2 | H-004 | Provision VPS (Oracle / Hetzner) | Soft · ops | 🔲 |
| 3 | H-011 | Kraken read-only keys in VPS `.env` | Hard · secrets | 🔲 |
| 4 | H-010 | Explicit live-trading approval (`TRENDALGO_MODE=live`) | Hard · go-live | 🔲 |
| 5 | H-028 | Per-exchange `go-live-gate.sh --approve` | Hard · go-live | 🔲 |
| 6 | H-032 | Worldwide trading phases + CEXes beyond nine (CEX-P4b) | Hard · expand CEX | 🔲 |
| 7 | H-035 / H-036 | DEX live program + **live** swap approve | Hard · expand DEX | 🔲 |
| 8 | DEX-P4a | `trading_enabled` Arbitrum / Ethereum after Base | Hard · expand DEX | 🔲 |
| 9 | H-017 | CoinStats parity compare + cancel sub (**deferred**) | Soft · deferred | 🔲 |
| 10 | H-026 | Monthly: portfolio integrity report | Recurring | 🔲 |
| 11 | H-027 | Monthly: VPS cost ≤ $10 | Recurring | 🔲 |
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
