# Monetization — Performance Software License

> Sprint 10 implementation. **Calculation-only** per ADR-0005/0008.

## Model

Monthly **performance-contingent software license** based on bot-attributed closed trades:

- Net-positive trades only; net-loss month = **$0**
- Default rate: **12%** of attributed profit (`config/founder.defaults.json`, H-029)
- Carry-forward credits; drawdown pause (M12)
- 7-day grace → suspend live trading on official build (not exchange access)

## Settlement

User **initiates** payment externally:

1. Monthly statement generated (M5)
2. User copies crypto address / scans QR (M7)
3. Optional Lightning invoice (user-initiated)
4. No operator verification of on-chain payment required for MVP (honor system + license gate)

## Rejected

Auto-withdraw, Stripe, fiat, custodial wallets.

## Reconciliation

Sprint 10: `scripts/reconcile-fees.sh` + `tests/test_billing/` (R-031).

## Related

- [`LICENSE_MODEL.md`](LICENSE_MODEL.md) — full structure (S10)
- [`LEGAL_SAFETY.md`](LEGAL_SAFETY.md)
- Feature specs: `docs/features/fee-*.md`
