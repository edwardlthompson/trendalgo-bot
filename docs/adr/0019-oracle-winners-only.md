# ADR 0019: Oracle winners-only trough→peak

- **Status:** Accepted
- **Date:** 2026-11-11
- **Deciders:** Product owner + agent

## Context

SIM-04 briefly made Oracle exit on every next peak, including losers (`H < entry L`),
so the spectrum audit could compare “honest” swing coverage. That contradicted
product copy (“perfect trough→peak”) and poisoned Secret Sauce baselines with
losing overlay bands.

## Decision

Restore winners-only Oracle: exit only when peak > entry and gross clears
round-trip fees. Densify pivots with order-1 fractals plus a 0.25% zigzag (capped).
Overlay Net % uses fee-aware `net_pnl/stake` when present. Spectrum gate still
allows `trial <= oracle*1.05`.

## Alternatives considered

- Keep loser-oracle and relabel UI — rejected; breaks SS honesty.
- 15m remap for denser swings — rejected; misaligns SS indexes with scan TF.

## Consequences

- Oracle win rate after fees is 100% (or zero trades).
- SIM-04 loser-oracle tests are amended; CHANGELOG notes the revert.
- Zigzag may raise trade count; hard cap 500 keeps SS runtime bounded.

### Critique

| Issue | Resolution |
| --- | --- |
| Spectrum “honest oracle” conflict | Gate already allows trial ≤ oracle×1.05; winners-only remains an upper bound |
| Zigzag explosion | Cap 500; constant in one place; unit test bounds |
