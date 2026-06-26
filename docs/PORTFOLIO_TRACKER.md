# Portfolio Tracker — CoinStats Replacement

> ADR-0004 · Sprint 5 core

## Goals

Self-hosted portfolio with Kraken sync, daily P/L, equity curve, and CoinStats/Delta-level UX (H-015).

## Data model (draft)

```sql
-- portfolio_snapshots (SQLite, Sprint 5)
-- id, captured_at, total_usd, holdings_json, source (kraken|manual)
-- cost_basis_lots — FIFO from Freqtrade closed trades
```

## Parity checklist (H-017)

| CoinStats feature | TrendAlgo | Sprint |
|-------------------|-----------|--------|
| Net worth hero | P1 | S5 |
| Daily P/L push | P2, NT1 | S5 |
| Holdings + cost basis | P4 | S5 |
| Allocation pie | P5 | S5 |
| Equity curve | P3, T5 | S5 |
| Multi-exchange | P12 | S8 |
| Timeline scrubber | P19 | S5 |

Validation: `bash scripts/compare-portfolio-parity.sh` (S5 exit).

## Monthly integrity

`bash scripts/check-portfolio-integrity.sh` (H-026).

## Related

- `docs/adr/0004-portfolio-tracker.md`
- R-017, R-022, R-026, R-028
