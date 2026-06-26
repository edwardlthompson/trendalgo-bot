# Feature Roadmap — TrendAlgo Bot

> Sprint 0 index. Detail in [`CANONICAL_PLAN.md`](CANONICAL_PLAN.md) feature matrix.

## Analysis summary

TrendAlgo combines a **native CCXT trading engine** (ADR-0010), **LTS scanner** (opportunity ranking), **self-hosted portfolio** (CoinStats replacement), and **AI-curated strategies** (not community marketplace). Differentiators vs pure bots: daily P/L UX, scanner-to-strategy pipeline, transparent performance license, multi-exchange roadmap (S13–S20).

## Feature ID index

| IDs | Domain | Sprint | Priority |
|-----|--------|--------|----------|
| T1–T36 | Trading bot & analytics | S1–S8 | MVP S1–4 |
| O1–O15 | Opportunity Scanner (LTS) | **S4.5** | v1 core |
| P1–P22 | Portfolio tracker | **S5** | v1 core |
| M1–M22 | Performance license | S10 | Product |
| AI5–AI8 | AI-recommended strategies | S11 | Growth |
| U1–U11, UX1–UX6 | UX & design | S3–S7 | Polish |
| NT1–NT4 | Notifications | S4.5–S5 | v1 core |
| OPS1–OPS5 | Backup, health, updates | S4 | Ops |
| L1–L5 | Legal | S0, S10 | Compliance |
| ~~IX1–IX2~~ | Community imports | — | **Rejected** |

## Sprint 0 deliverables

- ADR-0001–0009 drafted
- Domain scaffold `src/trendalgo/*`
- Feature spec stubs in `docs/features/`
- Integration docs: NATIVE_TRADING, EXCHANGE_ROADMAP, LTS, LEGAL, MONETIZATION

## Spec files

See `docs/features/` for vertical slice specs before Sprint 2+ implementation.
