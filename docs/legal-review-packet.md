# TrendAlgo Bot — Legal Review Packet

Generated: 2026-11-15T18:55:52Z

> **Not legal advice.** Packet for founder Tier A residual-risk review and optional counsel (Tier B / H-006b).

## Scope
- **Tier A:** owner-only + FOSS / source-available distribution (H-006 / H-022 / H-023)
- **Tier B:** non-owner commercial billing deferred (H-006b)
- Performance-contingent **software license** framing (not payment processing)
- User-initiated crypto settlement only; no auto-withdraw
- No KYC; pseudonymous install UUID; no custodial funds

## Included documents

---
## Source: `docs/adr/0007-legal-framework.md`

# ADR-0007: Legal Framework — Pseudonymous, Software-Only

- **Status:** Accepted (Sprint 0)
- **Date:** 2026-06-25

## Context

US/PR regulatory exposure for trading tools and performance-linked fees.

## Decision

1. **No KYC** — install UUID + terms version for consent log only.
2. **Software vendor framing** — not investment advice, not a broker/dealer.
3. **Data minimization** — no IP/email in fee ledger by default (`docs/DATA_MINIMIZATION.md`).
4. **Disclaimers** in UI, TERMS, and AI output (S7/S11).
5. **Tiered legal gates (ADR-0020):** Tier A founder residual-risk for owner-only + FOSS (H-006 / H-022 / H-023); Tier B counsel/clinic before non-owner billing (H-006b).

## Consequences

`docs/LEGAL.md`, TERMS; Legal Research Desk; pseudonymous referral/leaderboard S11.

---
## Source: `docs/adr/0008-legal-safe-monetization.md`

# ADR-0008: Legal-Safe Monetization — Anti-MSB

- **Status:** Accepted for Tier A (ADR-0020); Tier B counsel still required before non-owner charges (H-006b)
- **Date:** 2026-06-25 (tiered 2026-11-15)

## Context

Auto-collect from exchange accounts triggers MSB/money-transmitter risk. Retail crypto settlement must stay user-initiated.

## Decision

1. **Calculation-only** — billing module computes license amounts; never moves funds.
2. **Voluntary payment** — user sends crypto externally; operator never holds user keys for withdrawal.
3. **Non-custodial** — no pooled wallets, no Stripe, no auto-debit.
4. **CI enforcement** — `scripts/check-legal-compliance.sh` greps forbidden patterns (R-006 eliminated).
5. **Marketing** — never claim auto-collect or guaranteed fee extraction.

## Rejected

Stripe; auto-withdraw; institutional auto-collect; hosted custodial SaaS.

## Consequences

R-006 eliminated; Sprint 10 billing UX; `docs/LEGAL_SAFETY.md`.

**Gates (ADR-0020):** Tier A — founder residual-risk posture closes H-006 for owner-only + FOSS distribution. Tier B — H-006b blocks non-owner Alpha Share / performance-fee enrollment until counsel or clinic.

---
## Source: `docs/adr/0017-multi-user-monetization.md`

# ADR-0017 — Multi-user seams and performance-license terms

- **Status:** Accepted for the seams and the owner-approved terms (2026-10-09). Tier A (ADR-0020): FOSS publish + owner-only OK after founder residual-risk posture. Tier B: counsel/clinic (H-006b) still required before any **non-owner charge**. H-022 Tier A closes via Legal Research Desk + posture (license model docs); counsel before monetizing others.
- **Date:** 2026-10-09
- **Relates to:** ADR-0005 (amended by this ADR when Accepted), ADR-0008 (kept), ADR-0016 (host architecture), [docs/MONETIZATION.md](../MONETIZATION.md), [docs/LEGAL_SAFETY.md](../LEGAL_SAFETY.md), AGENTS.md (`distribution_tier: foss`)

## Context

- The owner wants to open the bot to other people later and to be compensated for building it. v1 is owner-only.
- ADR-0005 describes a performance-contingent license: a fee on bot-attributed net-positive closed trades, a 7-day grace period, and suspension of live trading when unpaid.
- The code does not match that model (verified 2026-10-09; register items M7 and M8):
  - `license_fee_for_trade` (`src/trendalgo/billing/profit.py`) charges 5% of each winning trade, and losses never offset wins. A month with $1,000 of wins and $900 of losses owes $50 under this code. A monthly net basis owes $5.
  - `apply_fee_rules` (`src/trendalgo/billing/rules.py`) only consumes the carry-forward credit. Nothing accrues it, so it stays at zero.
  - `GRACE_PERIOD_DAYS` is 7 (`src/trendalgo/billing/schema.py`).
  - The license gate returns before exits run (R5).
- ADR-0005 item 3 describes an AGPL codebase. The repo's root `LICENSE` file is MIT, and AGENTS.md sets `distribution_tier: foss`. That conflict is part of the tier decision in decision 8.

## Decision

1. **Tenant boundary.** One bot host, one owner, one set of exchange keys. No vendor-run bots for other people, no shared key storage, and no custodial service (ADR-0008).
2. **v1 is owner-only.** No accounts, billing, or payment flows ship in v1. Only the seams below are built.
3. **Seams built now (no user-visible features).**
   - `owner_id` on pairing, host rows, and every sync message. The host rejects a foreign `owner_id`.
   - Host profiles on the device (one in v1).
   - An `Entitlements` port on the host: `check(action, context) -> (allowed, reason)`. It gates new entries only, keeps the reason codes of `check_license_gate` (`dry_run`, `free_tier`, `licensed_until`, `ok`, `license_suspended`), and never gates exits.
   - A fills ledger with `owner_id`, a live flag, `plan_version`, and the bundle hash. Shadow fills never produce a statement line.
   - `publisher` and `kid` fields in plan bundles, so another signer can be accepted later.
4. **Performance-license terms.** The owner approved these as the recommended terms on 2026-10-09. Counsel review is still required before any non-owner charge.
   - Fee basis: net realized profit after exchange fees, summed per calendar month, on closed trades only. Unrealized gains never count.
   - High-water mark per host, across its bots. A fee is owed only on profit above the previous peak.
   - A losing month owes $0. Its loss reduces future fees through the high-water mark.
   - Trial: no fee until the trial ends (`billable_from`).
   - Rate: 5%, the documented `DEFAULT_LICENSE_RATE` (H-029).
   - Grace: 30 days after a statement, with reminders on day 0, 14, and 25.
   - No fee while the drawdown breaker is active.
   - The user starts every payment. There is no auto-collection and no auto-withdrawal (ADR-0008).
5. **Enforcement, official build only.** After the grace period, the official build opens no new entries for an unpaid host. Exits, stops, and flatten always run. Dry-run is never blocked. The code is MIT, so other builds are outside the product's control, and a determined user can build without the check. Payment depends on the official build being the best source of updates, the scanner, and the wizard.
6. **Attribution.** Only live fills count. The host computes statements from its own fills as a pure function, and no funds move. The device displays the statements.
7. **Fairness charter.**
   - Never block exits, stops, or flatten for non-payment.
   - No penalty fees, interest, or lock-in.
   - Statements are reproducible from the user's fills with a published formula. Fills can be exported at any time.
   - A closed statement period is never recalculated under new terms.
   - The owner's own host is not charged, because the owner is not an enrolled user.
8. **Distribution tier.** This ADR does not change `distribution_tier: foss`, and the code stays MIT. Any paid feature for other people needs a tier ADR first, after `commercial-compliance.mdc` review (M9).
9. **Legal scope before any non-owner charge (Tier B / H-006b).** Performance-fee and adviser-style rules, not only money transmission (M3). TERMS/privacy for fee enrollment (H-023 Tier B). Venue rules per jurisdiction before public billing copy (M4). Tier A FOSS publish does not require counsel (ADR-0020).
10. **Not in v1.** Stripe or fiat (rejected in ADR-0008), auto-withdraw, subaccount fee routing, vendor-run bots for others, and a strategy marketplace.

## Amends ADR-0005

- **Item 1 (fee basis):** from net-positive closed trades to monthly net realized profit with a high-water mark (decision 4).
- **Item 3 (AGPL codebase and billing boundary):** conflicts with the MIT `LICENSE`. Replaced by the open tier decision (decision 8).
- **Item 4 (7-day grace, suspension of live trading):** replaced by 30 days, with entry-only enforcement (decision 5).
- **Item 5 (net-loss months, drawdown pause):** consistent with decision 4, and kept.

## Consequences

- The fee code in `src/trendalgo/billing/` (`profit.py`, `rules.py`, `engine.py`, `schema.py`) must not produce any statement until P8 rewrites the math on the host, with rule tests.
- `docs/MONETIZATION.md` must not drive non-owner enrollment until P8 and Tier B (H-006b).
- The wizard shows fee terms as information for owner use; non-owner enrollment stays off until H-006b.
- FOSS / source-available public copy OK after Tier A posture (ADR-0020); fee marketing waits for Tier B.

## Alternatives considered

- **Per-trade fee (current code).** Rejected. Losses never offset wins, so a losing month can still owe a fee on gross wins (M7).
- **Stop exits on non-payment.** Rejected. An unpaid user's open positions would stay unmanaged (R5).
- **Auto-collection from exchange accounts.** Rejected by ADR-0008.
- **Voluntary sponsorship that does not depend on trade results.** Not adopted. It is lower risk, but it is not in the current docs and would need the same legal review. Recorded as a possible complement.

## Open items

- Tier A: H-006 / H-022 / H-023 via Legal Research Desk + founder residual-risk posture (ADR-0020).
- Tier B: H-006b counsel/clinic before non-owner charges (M3).
- Jurisdiction rules per venue before public billing copy (M4).
- Product license is ELv2 (ADR-0018); M9 AGPL/MIT conflict closed for product license.

---
## Source: `docs/adr/0018-elastic-license-v2.md`

# ADR-0018: Adopt Elastic License 2.0 (source-available)

- **Status:** Accepted (human approved 2026-11-11)
- **Date:** 2026-11-11
- **Supersedes:** ADR-0005 decision item 3 (AGPL codebase / billing-module license clause) only
- **Does not supersede:** ADR-0005 monetization shape (performance license, user-initiated settlement, grace/suspend, net-loss = $0) as amended by ADR-0017
- **Relates to:** ADR-0005, ADR-0017, [`docs/LICENSE_MODEL.md`](../LICENSE_MODEL.md), root [`LICENSE`](../../LICENSE)

## Context

ADR-0005 item 3 called for an **AGPL** codebase with a proprietary-friendly billing boundary. The root `LICENSE` remained **MIT**, and AGENTS.md set `distribution_tier: foss`. ADR-0017 documented that MIT/AGPL conflict and deferred a single license answer (open item M9 / tier decision).

Human decision 2026-11-11: ship as **source-available under Elastic License 2.0**, not OSI MIT/AGPL FOSS.

## Decision

1. **Product license is Elastic License 2.0 (ELv2).** SPDX: `Elastic-2.0`. Copyright holder: Edward L. Thompson (per `CITATION.cff`).
2. **Permitted use for operators:** free to run for their own trading.
3. **ELv2 limitations apply:** no providing the software to third parties as a hosted or managed service with substantial feature access; no moving/changing/disabling/circumventing license-key / billing protections; no removing licensor notices.
4. **Monetization shape stays** (ADR-0005 as amended by ADR-0017): performance-contingent fee, user-initiated settlement, official-build enforcement — not redefined here.
5. **Single answer:** ELv2 replaces both the MIT root file and the AGPL claim. Docs, badges, REUSE, `pyproject.toml`, and contributor guide must agree.

## Rejected

- Remain MIT OSI FOSS (insufficient protection against SaaS resale / billing strip).
- Switch to AGPL-3.0 (copyleft mismatch with intended commercial/source-available posture; conflicted with historical MIT file).
- Dual-license MIT+proprietary without a clear field-of-use license.

## Consequences

- Root `LICENSE`, `REUSE.toml`, `CITATION.cff` license field, `pyproject.toml`, README badge, and `docs/LICENSE_MODEL.md` use ELv2.
- ADR-0005 item 3 is superseded; monetization items remain.
- Risk R-012 framing shifts from “AGPL fork without billing” to “ELv2-noncompliant fork / stripped build” — official build value still matters.
- Template bootstrap helpers may still offer MIT/Apache for *child* template init; they do not redefine this product’s license.

---
## Source: `docs/adr/0020-legal-research-desk.md`

# ADR-0020: Legal Research Desk + tiered legal gates

- **Status:** Accepted
- **Date:** 2026-11-15
- **Deciders:** Founder (owner-only + FOSS ship scope)
- **Relates to:** ADR-0007, ADR-0008, ADR-0017, ADR-0018, H-006 / H-022 / H-023 / H-006b

## Context

Hard gates H-006, H-022, and H-023 required a paid attorney before public beta. That is unaffordable and blocked FOSS distribution of an owner-only product. An LLM “attorney bot” cannot practice law and must not mint “attorney approved” stamps.

## Decision

1. **Legal Research Desk** — in-repo Cursor skill `/legal-desk`, corpus under `docs/legal-desk/`, expanded legal packet. Output is research and consistency tooling **only**, with a mandatory not-legal-advice banner.
2. **Tier A (closable without counsel):** owner-only operation + public FOSS / source-available download after Founder Legal Posture, packet regen, TERMS/ELv2 alignment, and CI `check-legal-compliance`. Close H-006 / H-022 / H-023 via `founder_gate.py approve … --note "residual-risk owner-only+foss …"`.
3. **Tier B (deferred, hard):** non-owner commercial billing / performance-fee enrollment. Tracked as **H-006b**. Never AUTO. Requires real counsel, clinic, or equivalent before charging others.
4. **Ban fake counsel** — approve notes containing `attorney approved` are refused unless a file exists under `docs/legal-desk/counsel/`.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Attorney Grok Bot that “signs off” | Unauthorized practice of law; false security |
| Keep all legal gates blocked forever | Blocks FOSS publish of owner-only software |
| Close Tier B without counsel | Unacceptable residual risk for charging others |
## Consequences

- Public FOSS download OK after Tier A; billing enrollment UX stays off until H-006b.
- ADR-0008 / ADR-0017 status language updated to Tier A founder posture vs Tier B counsel.
- R-008 control: Tier A residual risk accepted by founder; Tier B still blocks fee beta.

### Critique

| Issue | Resolution |
|-------|------------|
| False “attorney approved” stamp | Ban phrase in approve notes; honesty banner on desk |
| Diluting R-008 | Tier B keeps non-owner billing hard |
| Empty posture file | Preflight fails closed until Accepted-scope + date |
| Stale sources | Date-stamp `sources.md`; desk skill re-checks links |
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
## Source: `docs/LEGAL.md`

# Legal Overview — TrendAlgo Bot

> **Not legal advice.** Tier A (owner-only + FOSS): founder residual-risk posture (H-006 / H-022 / H-023, ADR-0020). Tier B: counsel/clinic before non-owner billing (H-006b).

## Operator role

TrendAlgo Bot is **software** — a self-hosted tool that calculates signals, tracks portfolio, and computes performance license amounts. The operator is a **software vendor**, not:

- An investment adviser
- A broker-dealer or exchange
- A money services business (MSB)
- A custodian of user funds

## User responsibilities

- Own exchange accounts and API keys (trade-only, no Withdraw permission recommended)
- Initiate license payments externally when enrolled
- Comply with local tax and securities laws
- Accept TERMS version logged at enrollment (install UUID only)

## Document map

| Doc | Purpose |
|-----|---------|
| [`LEGAL_SAFETY.md`](LEGAL_SAFETY.md) | Prompt 8 anti-MSB rules |
| [`LEGAL.md`](LEGAL.md) | This overview + links |
| [`LICENSE_MODEL.md`](LICENSE_MODEL.md) | Performance license (Sprint 10) |
| [`DATA_MINIMIZATION.md`](DATA_MINIMIZATION.md) | GDPR/CCPA-aligned collection |
| [`adr/0007-legal-framework.md`](adr/0007-legal-framework.md) | ADR |
| [`adr/0008-legal-safe-monetization.md`](adr/0008-legal-safe-monetization.md) | ADR |
| [`adr/0020-legal-research-desk.md`](adr/0020-legal-research-desk.md) | Legal Research Desk + tiers |
| [`legal-desk/`](legal-desk/) | Desk corpus + `/legal-desk` |
| [`FOUNDER_LEGAL_POSTURE.md`](FOUNDER_LEGAL_POSTURE.md) | Tier A residual-risk checklist |
## Legal review packet

Generate: `bash scripts/generate-legal-review-packet.sh` (Tier A / optional Tier B counsel).

---
## Source: `docs/LEGAL_SAFETY.md`

# Legal Safety — Prompt 8 Monetization Rules

> **Hard constraints (ADR-0008).** CI enforces via `scripts/check-legal-compliance.sh`.

## Never ship

| Forbidden | Reason |
|-----------|--------|
| Auto-withdraw from exchange | MSB / custodial |
| Stripe or card processing for license | Money transmitter adjacency |
| Operator-held withdrawal keys | Custody |
| Subaccount fee routing | Custodial collection |
| Marketing "we collect your fees automatically" | Regulatory + R-006 |
| Community untrusted strategy imports | Liability (ADR-0009) |
| Hosted multi-tenant trading keys | Custodial SaaS |
## Always ship

| Required | Implementation |
|----------|----------------|
| Calculation-only license module | Sprint 10 M1–M4 |
| User-initiated settlement UX | Copy address + QR (M7/M22) |
| Terms + install UUID consent log | S10 L4 — no IP/email |
| Dry-run default | Until go-live gate |
| Software-only disclaimers | UI, TERMS, AI output |
| Trade-only API key guidance | `docs/SECURITY.md`, M11 |
## Edge cases (Sprint 10)

Documented in `docs/MONETIZATION.md`: withdraw-before-pay, partial fills, disputes, net-loss months, manual trades outside bot.

## Verification

```bash
bash scripts/check-legal-compliance.sh
python3 scripts/check_risk_mitigations.py --sprint 0

```

R-006 status: **eliminated**.

---
## Source: `docs/MONETIZATION.md`

# Monetization — Performance Software License

> Sprint 10 implementation + Audit-P6 (BILL-01…08). **Calculation-only** per ADR-0005/0008.

## Model

Monthly **performance-contingent software license** based on bot-attributed closed trades:

- Net-loss month = **$0** (lift-only floor never invents a fee)
- Default class: **Alpha Share**
- Opt-in class: **Standard Share** (raw equity net + equity HWM)
- Switch class any time; applies next period; no penalty

### Alpha Share formula

```
fee = rate * max(0, net - max(bh_net, 0))

```

Default rate: **5%** (`DEFAULT_LICENSE_RATE`). High-water mark tracks **cumulative excess**. Caps: `$5` lift-only floor, 30% of month profit, hard ceiling; deficit ages out at 6 months; drawdown pause at most once per quarter; HWM resets after 18 consecutive paid statements.

### Worked examples (5%)

| Case | net | bh_net | excess | fee |
|------|-----|--------|--------|-----|
| bull-beat | $200 | $80 | $120 | $6.00 |
| bull-trail | $50 | $120 | $0 | $0 |
| bear | $100 | -$40 | $100 | $5.00 |
Statement line items include net, B&H, excess, pinned reference prices, rate, fee, and whether floor/cap applied. Footer prints the Alpha Share formula verbatim.

## Settlement

User **initiates** payment to the operator's public address in **BTC, USDC, or USDT**:

1. Monthly statement generated (M5) — grace before live trading suspends
2. User picks asset (BTC on Bitcoin, USDC/USDT on Base) — app shows exact amount + QR
3. User sends from their own wallet — **no auto-withdraw, no custody**
4. Bot **polls the chain** and unlocks automatically
5. License active through end of the calendar month following the paid period

Configure `TRENDALGO_SETTLEMENT_ADDRESS` (BTC) and `TRENDALGO_SETTLEMENT_EVM_ADDRESS` (stablecoins). Dev/tests: `TRENDALGO_BTC_USD_RATE` + optional `TRENDALGO_PAYMENT_SIMULATE=1`.

## Rejected

Auto-withdraw, Stripe, fiat, custodial wallets.

## Evasion coverage (BILL-08)

| # | Vector | Control | Test id |
|---|--------|---------|---------|
| 1 | Patched `rate_pct` | Rate from enrollment / remote entitlement | `test_bill_06_identity` / enrollment store |
| 2 | Edited ledger | BILL-04 server recompute | `test_bill_04_integrity::test_delete_local_trade_raises_recompute_mismatch` |
| 3 | Offline operation | Grace then entry suspension; exits never gated | `test_grace_timeline::test_gate_refuses_new_entries_after_thirty_days_but_never_exits` |
| 4 | Clock rewind | BILL-05 monotonic day | `test_bill_05_monotonic::test_clock_rewind_does_not_extend_grace` |
| 5 | Fresh install | BILL-06 identity restore | `test_bill_06_identity::test_fresh_install_same_key_machine_restores_hwm` |
| 6 | Multi-instance | Seat count | `test_bill_06_identity::test_second_machine_without_seat_refused` |
| 7 | Manual exchange-UI trades | Accepted; documented as free (non-bot attribution) | `test_attribution` / signal_source filter |
| 8 | Mode reset to zero the period | Period from UTC calendar, not process state | `test_monthly_fee::test_months_are_utc_calendar_months` |
| 9 | Fund movement to a sub-account | Attribute by API key fingerprint, not balance | `test_bill_06_identity` |
| 10 | Splitting to duck a minimum | Floor applies per enrollment | `test_bill_03_caps::test_floor_lifts_small_fee_only` |
| 11 | Pause before month end | Pause quota 1/quarter (documented) | `test_bill_03_caps::test_pause_one_per_quarter_boundary` |
| 12 | Forced loss to trip the pause | BILL-03 pause cap | `test_bill_03_caps::test_forced_loss_cannot_suppress_two_quarters` |
| 13 | Carry-forward farming | BILL-03 deficit 6mo | `test_bill_03_caps::test_deficit_expires_after_six_months` |
| 14 | Forged API net | AUTH-01 + BILL-04 | `test_bill_04_integrity::test_forged_billing_post_rejected` |
| 15 | Zero-cent rounding | `_allocate` remainder lands | `test_monthly_fee::test_fee_shares_add_up_to_the_month_fee_exactly` |
| 16 | Midnight boundary | Venue fill timestamps (BILL-04) | `test_bill_04_integrity` / `fill_ts` on journal |
| 17 | Fork and strip | LIC-01 ELv2 | license / LIC tests |
| 18 | Permanent dry-run | Free tier; dry_run gate bypass only | `test_grace_timeline` dry_run path |
## Reconciliation

Sprint 10: `scripts/reconcile-fees.sh` + `tests/test_billing/` (R-031).

## Related

- [`LICENSE_MODEL.md`](LICENSE_MODEL.md) — full structure (S10)
- [`LEGAL_SAFETY.md`](LEGAL_SAFETY.md)
- Feature specs: `docs/features/fee-*.md`

---
## Source: `docs/LICENSE_MODEL.md`

# License Model (Draft)

> Sprint 10 publish. Attorney review before public beta (H-023).
> Product license: Elastic License 2.0 (ELv2) — human approved 2026-11-11. See ADR-0018.

## Structure

1. **Source-available (ELv2)** — free to run for your own trading; no reselling as a hosted service; no stripping billing/license-key protections
2. **Free tier** — dry-run, limited history
3. **Performance license** — % of bot-attributed net-positive closed trades (default 5%)
4. **Boost tier (B1)** — optional higher rate for premium AI strategy docs (S11)

## Terms sections (outline)

1. Software-only disclaimer
2. Not investment advice
3. User-initiated payment obligation after grace
4. Bot-attributed trades definition
5. Net-loss = $0 license
6. ELv2 + official build value-add (no hosted SaaS resale; billing protections intact)
7. Limitation of liability
8. Puerto Rico / US governing law (attorney to finalize)

Full draft: Sprint 10 `TERMS.md` from this outline. **Published:** root [`TERMS.md`](../../TERMS.md) (attorney review pending H-023).

See [`MONETIZATION.md`](MONETIZATION.md), ADR-0005 (monetization shape), and ADR-0018 (ELv2).

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
## Source: `docs/FOUNDER_LEGAL_POSTURE.md`

# Founder Legal Posture (Tier A)

> **Not legal advice.** By filling the fields below you accept residual regulatory risk for the stated scope.
> Desk: [`docs/legal-desk/`](legal-desk/) · ADR: [`docs/adr/0020-legal-research-desk.md`](adr/0020-legal-research-desk.md)

## Accepted scope

```
Accepted-scope: owner-only+foss
Accepted-date: 2026-11-15
Accepted-by: Edward L. Thompson (founder)

```

## Checklist (founder)

- [x] I understand the Legal Research Desk is **not** a licensed attorney and does not provide legal advice.
- [x] Ship scope is **owner-only** operation plus public **FOSS / source-available** download (ELv2).
- [x] I will **not** enroll or charge non-owners Alpha Share / performance fees until **H-006b** (counsel or clinic).
- [x] Product keeps ADR-0008 controls: calculation-only billing math, user-initiated settlement, no custody, dry-run default until go-live gates.
- [x] I have reviewed TERMS.md, LEGAL.md, LEGAL_SAFETY.md, and the generated legal-review-packet.

## Explicitly deferred (Tier B)

- Non-owner performance-license enrollment UX
- Public marketing that requires others to pay a performance fee
- Any auto-collection or custodial payment path (already forbidden)

## Approve commands (after this file is filled)

```bash
python scripts/founder_gate.py approve H-006 --note "residual-risk owner-only+foss ADR-0020"
python scripts/founder_gate.py approve H-022 --note "residual-risk owner-only+foss license ADRs"
python scripts/founder_gate.py approve H-023 --note "residual-risk owner-only+foss TERMS ELv2"

```

---
## Source: `TERMS.md`

# TrendAlgo Bot — Terms of Use

> **Not legal advice.** Software-tool terms for owner-operated installs and public source-available distribution (Tier A, ADR-0020).
> Non-owner performance-fee enrollment is **not offered** until Tier B (H-006b). Founder residual-risk posture: `docs/FOUNDER_LEGAL_POSTURE.md`.

## 1. Software only

TrendAlgo Bot is self-hosted **software**. The operator is a software vendor, not a broker, exchange, investment adviser, money transmitter, or custodian.

## 2. Not investment advice

Signals, backtests, scanners, and AI commentary are informational tools. You are solely responsible for trading decisions and for complying with laws that apply to you.

## 3. License (ELv2)

The product is licensed under the **Elastic License 2.0** (see root `LICENSE` and `docs/LICENSE_MODEL.md`). You may run it for your own trading. ELv2 limitations apply (no providing the software to third parties as a hosted/managed service with substantial feature access; no circumventing license/billing protections; no removing notices).

## 4. Performance license — Tier B (not offered yet)

Optional performance-contingent software license terms (monthly net / high-water mark, user-initiated settlement, entry-only enforcement) are described in `docs/MONETIZATION.md` and ADR-0017 for a **future** enrollment path. **They are not offered to non-owners in this TERMS version.** Official builds must not enroll or charge others until H-006b is cleared.

## 5. No auto-collection

TrendAlgo never holds withdrawal keys, auto-withdraws, or routes subaccount fees. Any future settlement is user-initiated (copy address / QR) only. Stripe/card processing for license fees is out of scope (ADR-0008).

## 6. Dry-run default

Live trading stays off until you explicitly pass go-live gates. Dry-run / paper paths are never blocked by license state.

## 7. Limitation of liability

Software is provided “as is” without warranties. See `docs/LEGAL.md`.

## 8. Governing law

Puerto Rico / United States — founder entity details are the operator’s responsibility. This section is a venue placeholder, not a counsel opinion.

## 9. Consent log

Acceptance records: TERMS version + timestamp + install UUID only (no IP, no email) per data-minimization policy.

Version: `2026-11-15-tier-a-1`

---
## Source: `BUILD_PLAN.md`

# TrendAlgo Bot — BUILD_PLAN

<!-- remaining-tally -->
**Remaining:** AGENT 1 · LOCAL 0 · CLOUD 1 · AUTO 0 · HUMAN 0 · ADB 0 · **1 open**
<!-- /remaining-tally -->
<!-- tally note: Multi-venue Sequential archived 2026-11-15 -->
> **Detail:** [`docs/specs/audit-remediation.md`](docs/specs/audit-remediation.md) · [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
> **Completed work:** [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · **Post-delivery:** [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · **Exchange:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md) · **DEX:** [`docs/DEX_ROADMAP.md`](docs/DEX_ROADMAP.md) · **Support:** [`docs/SUPPORT_MATRIX.md`](docs/SUPPORT_MATRIX.md)
> **Sauce / Market Context / logos** archived in COMPLETED_TASKS.md @ `665d6f5` · v1.15.2.
> **Multi-venue Sequential (CEX/DEX/TF)** archived in COMPLETED_TASKS.md (2026-11-15).
> **Honesty DoD (every multi-venue AGENT row):** bump [`support_matrix.json`](src/trendalgo/device/data/support_matrix.json) + [`docs/SUPPORT_MATRIX.md`](docs/SUPPORT_MATRIX.md) + README Exchange / today / coming-soon + `about_line` when capability changes; scoped `test_support_matrix.py` green.

### Product (do not drift)

<!-- product-brief-sync:begin -->
> Read `AGENT.md` before any sprint row.

**One-liner:** Photoreal Cycles icons from a locked seed, camera, and lighting.
**Do not drift:** camera, messages, tame, neon

**Rules:**
- Generate store/PWA icons from a JSON manifest (seed, camera, lighting).
- Machine QA only — do not ask a human to review thousands of frames.
- Cycles OptiX is local GPU; CI stays CPU/headless or skip if Blender is missing.
- Do not overwrite live `branding/assets/*.svg` (Sacred vector SoT).

**First milestone:** Seeded icon factory with QA JSON; sample manifest in CI; 4000+ run on This Computer.
<!-- product-brief-sync:end -->

## Now

> Day-to-day device: `.\scripts\packaging\relaunch-device.ps1` (source-first; no PyInstaller).
> Follow-ups: LIVE/NOTIF botd cron wiring; SIM snapshot regen; Tier A legal posture (H-006/H-022/H-023) + H-006b before non-owner billing (ADR-0020).

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |
### Sequential (agent)

> **Multi-venue Sequential (CEX/DEX/TF)** + TF-P2…P4 archived in COMPLETED_TASKS.md (2026-11-15). LOCAL lane clear; remaining AGENT is DEX-P4b `[CLOUD]`.

### Human work (complete in this order)

> Single pack for all founder actions. Soft/optional first only when it unblocks nothing critical — **legal → ops → secrets → live → expand**. Detail + approve CLI: [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · [`docs/FOUNDER_GATES.md`](docs/FOUNDER_GATES.md). Hard gates never AUTO.

| # | ID | Task | Kind | Status |
|---|----|------|------|--------|
| 1 | H-006 | Tier A: ADR-0008 + residual-risk owner-only+foss (ADR-0020) | Hard · legal Tier A | 🔲 |
| 2 | H-022 | Tier A: license ADRs via Legal Research Desk + posture | Hard · legal Tier A | 🔲 |
| 3 | H-023 / R-Audit-8.9 | Tier A: TERMS + packet + FOUNDER_LEGAL_POSTURE | Hard · legal Tier A | 🔲 |
| 3b | H-006b | Tier B: counsel/clinic before non-owner billing | Hard · legal Tier B | 🔲 |
| 4 | H-007 | Approve ADR-0001 / S1 (after `validate-bootstrap --quick`) | Soft · bootstrap | 🔲 |
| 5 | H-003 | Branch protection (`setup-github-repo.sh`) | Soft · GitHub | 🔲 |
| 6 | H-004 | Provision VPS (Oracle / Hetzner) | Soft · ops | 🔲 |
| 7 | H-008 | Telegram token in VPS `.env` | Hard · secrets | 🔲 |
| 8 | H-011 | Kraken read-only keys in VPS `.env` | Hard · secrets | 🔲 |
| 9 | PF-H1 | Optional: CoinMarketCal / Coindar API keys (calendar wizard; CI ok without) | Soft · optional | 🔲 |
| 10 | CEX-P3c | Optional: pay for per-venue historical packs | Soft · cost | 🔲 |
| 11 | H-010 | Explicit live-trading approval (mode=live) | Hard · go-live | 🔲 |
| 12 | H-028 | Per-exchange `go-live-gate.sh --approve` (every venue) | Hard · go-live | 🔲 |
| 13 | H-032 / CEX-P4b | Worldwide trading ack + CEXes beyond nine (P1-first) | Hard · expand CEX | 🔲 |
| 14 | H-035 / H-036 | DEX live program + live swap approve | Hard · expand DEX | 🔲 |
| 15 | DEX-P4a | Enable `trading_enabled` Arbitrum / Ethereum after Base proven | Hard · expand DEX | 🔲 |
| 16 | H-017 | CoinStats parity compare + cancel sub (**deferred**) | Soft · deferred | 🔲 |
| 17 | H-026 | Monthly: portfolio integrity report | Recurring | 🔲 |
| 18 | H-027 | Monthly: VPS cost ≤ $10 | Recurring | 🔲 |
Founder preflights S0–S12: fold into #4–#8 as you run `python scripts/founder_gate.py status`. Local preview: [`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md) · Post-delivery: [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md).

---

## Open work

### Multi-venue parity (AGENT / Cloud — after Human #13–#15 where gated)

- 🔲 [AGENT][CLOUD] DEX-P4b New swap plugins after P1–P2 — scope: `src/trendalgo/venues/`

### Maintenance cadence

| Cadence | Owner | Item |
|---------|-------|------|
| Weekly | AUTO | `check_risk_mitigations.py` · CI/CodeQL on `main` · Dependabot triage |
| Monthly | AUTO / Human #17–#18 | portfolio integrity · production cost · backup dry-run (R-020) |
| Pre-live | AUTO + Human #11–#12 | `go-live-gate.sh --check-only` → `--approve` |
---

## Owner labels

| Label | Owner |
|-------|-------|
| `AGENT` | Code, docs, tests |
| `HUMAN` | Credentials, legal, go-live |
| `AUTO` | CI / gate scripts |
**Hard gates (never AUTO):** H-006, H-006b, H-008, H-010, H-011, H-023, H-028, H-031, H-032, H-036 · Tier A legal closes with `residual-risk owner-only+foss` note (ADR-0020); Tier B billing stays deferred

---

## Completed

Finished BUILD_PLAN rows live in [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md).

<!-- ux-inventory -->
| ID | Change | Status |
|----|--------|--------|
| UX-004 | Settings: danger-styled Remove key + confirm before delete | planned |
| UX-005 | Settings: scroll-to / deep-link section from empty-state CTAs | planned |
| UX-006 | Scanner chrome: action buttons; board filters + 2-col Settings; Status dialog | done |
| UX-007 | Backtest chrome: same strip pattern; Color ranks/Perfect in Settings Results view | done |
<!-- /ux-inventory -->

## News inbox (synced)

P1/P2 tasks auto-synced by News Bot from [`docs/NEWS_INBOX.md`](docs/NEWS_INBOX.md).

> Security onboarding API-key hygiene (news P2) archived in COMPLETED_TASKS.md (2026-11-15).

## Checklist (Tier A founder)
- [ ] LEGAL_SAFETY Never/Always still match the product
- [ ] TERMS.md is ELv2 / software-tool; fee enrollment marked Tier B
- [ ] FOUNDER_LEGAL_POSTURE.md has Accepted-scope + Accepted-date
- [ ] CI: `bash scripts/check-legal-compliance.sh`

## Checklist (Tier B counsel / clinic — H-006b)
- [ ] Performance license framing vs MSB / money transmission (PR/US)
- [ ] Adviser-style / performance-fee rules before non-owner charges
- [ ] User-initiated settlement copy — no auto-collect claims
- [ ] Data minimization — no IP/email in consent log
