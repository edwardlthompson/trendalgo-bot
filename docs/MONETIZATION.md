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
