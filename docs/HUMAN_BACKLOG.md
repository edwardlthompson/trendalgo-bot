# HUMAN Backlog — TrendAlgo Bot

> **Single source of truth** for founder actions. BUILD_PLAN lists **AGENT/AUTO only** — all `[HUMAN]` gates live here.
>
> **Automation:** `python scripts/founder_gate.py preflight H-00N` · `approve H-00N` · `approve-all-soft` · `preflight-sprint --sprint N`
>
> **Exchange program gates:** H-030–H-034 · **Post-delivery matrix:** [`docs/POST_DELIVERY_PLAN.md`](POST_DELIVERY_PLAN.md)

## How to clear items

| Type | Command |
|------|---------|
| After preflight PASS | `python scripts/founder_gate.py approve H-00N` |
| All soft gates (batch) | `python scripts/founder_gate.py approve-all-soft` |
| Pre-Sprint-1 bundle | `python scripts/founder_gate.py approve-bundle pre-sprint-1` |
| Sprint gates | `python scripts/founder_gate.py preflight-sprint --sprint N` |

**Hard gates (never AUTO-approve):** H-006, H-008, H-010, H-011, H-023, H-028, **H-031**, **H-032**, **H-036**

---

## Master tier table — DEX Plugin Program (S21+)

| ID | Item | Tier | AUTO preflight | Blocks |
|----|------|------|----------------|--------|
| H-035 | DEX program scope (S21–S24 incl. dry-run swaps) | soft | ✅ | S21+ AGENT work |
| H-036 | DEX live swap trading | **hard** | ⚠️ registry v4 + RUNBOOK | S24 live |

**H-035 preflight:** `docs/DEX_ROADMAP.md` + `src/trendalgo/dex/` present.

**H-036 preflight:** `config/venues.registry.json` `dex_live_phase` + RUNBOOK DEX section.

---

## Master tier table — Exchange Program (S13+)

| ID | Item | Tier | AUTO preflight | Blocks |
|----|------|------|----------------|--------|
| H-021 | Old second-exchange choice | superseded | — | → H-030 |
| H-030 | Exchange program + native-only scope | soft | ✅ | S13 AGENT work |
| H-031 | ADR-0010 + approve Freqtrade removal | **hard** | ⚠️ ADR exists | S15 |
| H-032 | Worldwide bot trading phases | **hard** | ⚠️ roadmap § Tier D | S18 |
| H-034 | Local preview sign-off (L1+ per sprint) | soft | ✅ | S13+ commits |

**H-030 preflight:** `docs/EXCHANGE_ROADMAP.md` + BUILD_PLAN S13 section present.

**H-031 preflight:** `docs/adr/0010-ccxt-native-engine.md` present (approve = explicit FT removal consent).

**H-034 preflight:** `docs/LOCAL_DEV.md` + `scripts/dev-local.ps1` present.

---

## Master tier table — Post-delivery (S0–S12)

| ID | Sprint | Item | Tier | AUTO preflight | Blocks |
|----|--------|------|------|----------------|--------|
| H-001 | S0 | Repo name, origin, README | soft | ✅ | Pre-Sprint-1 |
| H-002 | S0 | Pick Cursor mode | optional | ✅ | — |
| H-004 | S0 | VPS hosting (Oracle / Hetzner) | soft | ✅ | S4 deploy |
| H-005 | S0 | Founder defaults | soft | ✅ | — |
| H-006 | S0 | Attorney + ADR-0008 | **hard** | ⚠️ legal packet | Public beta |
| H-007 | S1 | ADR-0001 / S1 scope | soft | ✅ | Pre-Sprint-1 |
| H-008 | S2 | Telegram token | **hard** | ⚠️ `.env` | Alerts |
| H-009 | S3 | Playwright smoke | soft | ✅ | — |
| H-010 | S4 | Live-trading approval | **hard** | ✅ script | Live orders |
| H-011 | S4 | Kraken read-only keys | **hard** | ⚠️ `.env` | Portfolio sync |
| H-012 | S4 | Production cost check | soft | ✅ | — |
| H-013 | S4.5 | LTS absorption scope | soft | ✅ S4 preflight | Archive path |
| H-014 | S4.5 | Archive LTS repo | soft | ✅ parity script | Deprecation |
| H-015 | S5 | S5 scope / UI bar | soft | ✅ S5 preflight | — |
| H-016 | S5 | Notification hour | soft | ✅ smoke | Daily P/L |
| H-017 | S5 | CoinStats parity | soft | ✅ parity script | Cancel CoinStats |
| H-018 | S6 | S6 scope (templates) | soft | ✅ S6 preflight | — |
| H-019 | S7 | S7 scope (analytics) | soft | ✅ S7 preflight | — |
| H-020 | S8 | S8 scope (multi-exchange) | soft | ✅ S8 preflight | — |
| H-022 | S10 | License ADR attorney | **hard** | ⚠️ legal docs | Public beta |
| H-023 | S10 | TERMS sign-off | **hard** | ⚠️ TERMS.md | Distribution |
| H-024 | S11 | S11 scope (no marketplace) | soft | ✅ S11 preflight | — |
| H-025 | S12 | On-chain provider | soft | ✅ S12 preflight | On-chain live |

---

## Ongoing / maintenance

| ID | Cadence | Item | AUTO | Human |
|----|---------|------|------|-------|
| H-026 | Monthly | Portfolio integrity | ✅ script | Review report |
| H-027 | Monthly | VPS cost ≤ $10 | ✅ script | Confirm invoice |
| H-028 | Every go-live | Repeat H-010 checklist | ✅ script | Explicit approve |

---

## Fully automated (appendix — not in backlog)

H-003 · H-009 · H-012 · H-029 · H-005 (defaults applied)

---

## Pre-Sprint-1 bundle

```bash
python scripts/founder_gate.py preflight H-001
python scripts/founder_gate.py preflight H-005
python scripts/founder_gate.py preflight H-007
python scripts/founder_gate.py approve-bundle pre-sprint-1
```

**Exchange program start:**

```bash
python scripts/founder_gate.py preflight H-034
python scripts/founder_gate.py approve H-034 --note "L1 preview OK"
python scripts/founder_gate.py preflight H-030
python scripts/founder_gate.py approve H-030
```

**Full reference:** [`docs/FOUNDER_GATES.md`](FOUNDER_GATES.md) · [`docs/CANONICAL_PLAN.md`](CANONICAL_PLAN.md)
