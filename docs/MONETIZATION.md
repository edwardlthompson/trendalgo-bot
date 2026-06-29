# Monetization — Performance Software License

> Sprint 10 implementation. **Calculation-only** per ADR-0005/0008.

## Model

Monthly **performance-contingent software license** based on bot-attributed closed trades:

- Net-positive trades only; net-loss month = **$0**
- Default rate: **5%** of attributed profit (`DEFAULT_LICENSE_RATE`, H-029)
- Carry-forward credits; drawdown pause (M12)
- 7-day grace → suspend live trading on official build (not exchange access)

## Settlement

User **initiates** payment to the operator's public address in **BTC, USDC, or USDT**:

1. Monthly statement generated (M5) — 7-day grace before live trading suspends
2. User picks asset (BTC on Bitcoin, USDC/USDT on Base) — app shows exact amount + QR
3. User sends from their own wallet — **no auto-withdraw, no custody**
4. Bot **polls the chain** (Blockstream for BTC, Base RPC for ERC-20) and unlocks automatically
5. License active through end of the calendar month following the paid period

Configure `TRENDALGO_SETTLEMENT_ADDRESS` (BTC) and `TRENDALGO_SETTLEMENT_EVM_ADDRESS` (stablecoins). Dev/tests: `TRENDALGO_BTC_USD_RATE` + optional `TRENDALGO_PAYMENT_SIMULATE=1`.

## Rejected

Auto-withdraw, Stripe, fiat, custodial wallets.

## Reconciliation

Sprint 10: `scripts/reconcile-fees.sh` + `tests/test_billing/` (R-031).

## Related

- [`LICENSE_MODEL.md`](LICENSE_MODEL.md) — full structure (S10)
- [`LEGAL_SAFETY.md`](LEGAL_SAFETY.md)
- Feature specs: `docs/features/fee-*.md`
