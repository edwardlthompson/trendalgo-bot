# ADR-0017 — Multi-user seams and performance-license terms

- **Status:** Accepted for the seams and the owner-approved terms (2026-10-09). Counsel sign-off under H-006 is still required before any non-owner use, and H-022 attorney review of ADR-0005 is still open.
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
9. **Legal scope before any non-owner charge.** H-006 must cover performance-fee and adviser-style rules, not only money transmission (M3). H-023 covers the terms and privacy text. Venue rules per jurisdiction are needed before public copy (M4).
10. **Not in v1.** Stripe or fiat (rejected in ADR-0008), auto-withdraw, subaccount fee routing, vendor-run bots for others, and a strategy marketplace.

## Amends ADR-0005

- **Item 1 (fee basis):** from net-positive closed trades to monthly net realized profit with a high-water mark (decision 4).
- **Item 3 (AGPL codebase and billing boundary):** conflicts with the MIT `LICENSE`. Replaced by the open tier decision (decision 8).
- **Item 4 (7-day grace, suspension of live trading):** replaced by 30 days, with entry-only enforcement (decision 5).
- **Item 5 (net-loss months, drawdown pause):** consistent with decision 4, and kept.

## Consequences

- The fee code in `src/trendalgo/billing/` (`profit.py`, `rules.py`, `engine.py`, `schema.py`) must not produce any statement until P8 rewrites the math on the host, with rule tests.
- `docs/MONETIZATION.md` still describes the older model. It must not be shown to non-owners until P8 and counsel sign-off.
- The wizard shows the fee terms at step W0, and again before the first live order for non-owner use. Owner use shows them as information only.
- Public copy waits for counsel review (H-006, H-023).

## Alternatives considered

- **Per-trade fee (current code).** Rejected. Losses never offset wins, so a losing month can still owe a fee on gross wins (M7).
- **Stop exits on non-payment.** Rejected. An unpaid user's open positions would stay unmanaged (R5).
- **Auto-collection from exchange accounts.** Rejected by ADR-0008.
- **Voluntary sponsorship that does not depend on trade results.** Not adopted. It is lower risk, but it is not in the current docs and would need the same legal review. Recorded as a possible complement.

## Open items

- H-006 scope (M3), H-022 review of ADR-0005, and H-023 terms.
- Jurisdiction rules per venue (M4).
- Tier and license decision (M9), including the AGPL and MIT conflict in ADR-0005 item 3.
