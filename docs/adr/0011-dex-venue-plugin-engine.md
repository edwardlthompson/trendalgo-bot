# ADR-0011: DEX Venue Plugin Engine

- **Status:** Accepted (DEX Plugin Program S21+)
- **Date:** 2026-06-26
- **Deciders:** Project team

## Context

S12 shipped a monolithic `portfolio/onchain.py` stub for EVM wallet read. The DEX program (S21–S24) requires multi-chain portfolio and optional swap plugins without hardcoding chain logic in API routes (CM-8).

## Decision

1. **Registry:** `config/venues.registry.json` drives chain/venue metadata (EVM + Solana in S21).
2. **Plugins:** `src/trendalgo/venues/` — `WalletReadPlugin` ABC; EVM and Solana implementations.
3. **Orchestration:** `venues/wallet_sync.py` syncs balances; `portfolio/onchain.py` delegates for backward compatibility.
4. **RPC:** Per-chain env vars (`ETH_RPC_URL`, `BASE_RPC_URL`, `ARB_RPC_URL`, `SOLANA_RPC_URL`); live read requires `ONCHAIN_SYNC_ENABLED=1`.
5. **Trading (S23+):** Swap plugins and `dex/runner/` added in later sprints; S21 is wallet read only.
6. **Signer (S23–S24):** `DEX_SIGNER_KEY` on VPS only — never in API, logs, or git (CM-9).

## Consequences

- API exposes `GET /platform/venues/registry`; onchain routes validate `chain` against registry.
- H-035 blocks S21+ AGENT work until DEX program scope approved.
- H-025 blocks live RPC until founder provides endpoints.

## Alternatives considered

| Option | Rejected because |
|--------|------------------|
| Hardcode chains in `onchain.py` | CM-8; does not scale to S22–S24 venues |
| Paid indexers (Alchemy tier) | Cost + FOSS policy; public RPC env-only |
| web3.py dependency | Heavy deps; urllib JSON-RPC sufficient for native balance read |

## Verification

- CM-8: no chain list in `platform.py`; registry-driven validation
- S21 tests: four venues dry-run + registry API
- Dry-run default preserved
