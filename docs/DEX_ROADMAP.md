# DEX Plugin Program Roadmap

> **Status:** Complete (S21–S24) · **Engine:** ADR-0011 venue plugins · **Human gates:** H-035, H-036, H-025
> **Related:** [`BUILD_PLAN.md`](../BUILD_PLAN.md) · [`docs/adr/0011-dex-venue-plugin-engine.md`](adr/0011-dex-venue-plugin-engine.md)

## Goal

Multi-chain DEX portfolio read and phased swap execution via a registry-driven plugin engine — separate from the CEX exchange program (ADR-0010).

## S21 — Foundation ✅ AGENT

- `config/venues.registry.json` — ethereum, base, arbitrum, solana (wallet read)
- `src/trendalgo/venues/` plugin registry + EVM/Solana wallet read
- RPC via env; dry-run default

## S22 — Portfolio plugins ✅ AGENT

Uniswap V3 LP, 0x quote preview, multi-chain sync orchestration + billing attribution by venue.

## S23 — Dry-run swaps ✅ AGENT

Swap simulation only; `DEX_TRADING_ACK` gate; no mainnet broadcast.

## S24 — Live swaps + ops ✅ AGENT

Per-venue go-live; `DEX_SIGNER_KEY` on VPS; runbook for RPC failover. Registry v4 · Base Phase 1 live.

## Human gates

| ID | Blocks |
|----|--------|
| H-035 | All S21+ AGENT work |
| H-025 | Live RPC endpoints |
| H-036 | S24 live swaps |
