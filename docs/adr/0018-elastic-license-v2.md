# ADR-0018: Adopt Elastic License 2.0 (source-available)

- **Status:** Accepted (human approved 2026-11-11)
- **Date:** 2026-11-11
- **Supersedes:** ADR-0005 decision item 3 (AGPL codebase / billing-module license clause) only
- **Does not supersede:** ADR-0005 monetization shape (performance license, user-initiated settlement, grace/suspend, net-loss = $0) as amended by ADR-0017
- **Relates to:** ADR-0005, ADR-0017, [`docs/LICENSE_MODEL.md`](../LICENSE_MODEL.md), root [`LICENSE`](../../LICENSE)

## Context

ADR-0005 item 3 called for an **AGPL** codebase with a proprietary-friendly billing boundary. The root `LICENSE` remained **MIT**, and AGENTS.md set `distribution_tier: foss`. ADR-0017 documented that MIT/AGPL conflict and deferred a single license answer (open item M9 / tier decision).

Human decision 2026-11-11: ship as **source-available under Elastic License 2.0**, not OSI MIT/AGPL FOSS.

## Decision

1. **Product license is Elastic License 2.0 (ELv2).** SPDX: `Elastic-2.0`. Copyright holder: Edward L. Thompson (per `CITATION.cff`).
2. **Permitted use for operators:** free to run for their own trading.
3. **ELv2 limitations apply:** no providing the software to third parties as a hosted or managed service with substantial feature access; no moving/changing/disabling/circumventing license-key / billing protections; no removing licensor notices.
4. **Monetization shape stays** (ADR-0005 as amended by ADR-0017): performance-contingent fee, user-initiated settlement, official-build enforcement — not redefined here.
5. **Single answer:** ELv2 replaces both the MIT root file and the AGPL claim. Docs, badges, REUSE, `pyproject.toml`, and contributor guide must agree.

## Rejected

- Remain MIT OSI FOSS (insufficient protection against SaaS resale / billing strip).
- Switch to AGPL-3.0 (copyleft mismatch with intended commercial/source-available posture; conflicted with historical MIT file).
- Dual-license MIT+proprietary without a clear field-of-use license.

## Consequences

- Root `LICENSE`, `REUSE.toml`, `CITATION.cff` license field, `pyproject.toml`, README badge, and `docs/LICENSE_MODEL.md` use ELv2.
- ADR-0005 item 3 is superseded; monetization items remain.
- Risk R-012 framing shifts from “AGPL fork without billing” to “ELv2-noncompliant fork / stripped build” — official build value still matters.
- Template bootstrap helpers may still offer MIT/Apache for *child* template init; they do not redefine this product’s license.
