# Public Roadmap

> High-level phases. Detail in [`BUILD_PLAN.md`](../BUILD_PLAN.md) and [`FEATURE_ROADMAP.md`](FEATURE_ROADMAP.md).

## Phase 1 — MVP (Sprints 1–4)

Native CCXT Kraken dry-run (Freqtrade removed in S15 / ADR-0010) → live on external VPS after go-live gates; web dashboard; Telegram alerts (outbound; ingress optional); TradingView webhooks (**signal ingress / audit only** unless `TV_EXECUTION_ACK=1`).

## Phase 2 — v1 Core (S4.5–5)

LTS Opportunity Scanner; CoinStats-class portfolio; daily P/L notifications.

## Phase 3 — v1 Extended (S6–8)

Strategy templates, multi-bot, analytics, second exchange read-only portfolio.

## Phase 4 — License (S10)

Performance software license; fee dashboard; user-initiated settlement (on-chain). Lightning invoicing is **not available** until a real node is wired. TERMS / attorney review still required for public beta (H-006 / H-023).

## Phase 5 — Growth (S11)

AI-recommended strategies; anonymous referral; **no community marketplace**.

## Phase 6 — Platform (S12)

SQLite MVP default; **Postgres dual-write is experimental / not production-default**; on-chain read-only; Risk Register Zero.

## Phase 7 — Exchange program (S13–S20)

Multi-exchange registry; native CCXT US trading (S15–S17); worldwide Phase 1 (S18); Phase 2 + arbitrage (S19); N-exchange ops (S20). **AGENT complete** — live worldwide still requires H-032. Detail: [`docs/EXCHANGE_ROADMAP.md`](EXCHANGE_ROADMAP.md).

## Phase 8 — DEX plugin program (S21–S24)

Multi-chain wallet read (EVM + Solana); Uniswap V3 LP + 0x quotes; dry-run swaps; **live swaps Base Phase 1 only** (other chains read-only). **AGENT complete** — live DEX requires H-035/H-036. Detail: [`docs/DEX_ROADMAP.md`](DEX_ROADMAP.md).

## Rejected (permanent)

Community strategy marketplace, custodial SaaS, auto-withdraw monetization, Stripe billing.
