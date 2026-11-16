---
name: legal-desk
description: Run the Legal Research Desk — research memos and Tier A posture checks. Not legal advice. Use when /legal-desk or founder legal gates.
disable-model-invocation: false
---

# Legal Research Desk

See also: `.cursor/commands/legal-desk.md`, `docs/legal-desk/README.md`, `docs/adr/0020-legal-research-desk.md`

> **Not legal advice.** Not a licensed attorney. Residual risk remains with the founder.
> Never brand output as an “Attorney Bot” or write “attorney approved.”

## Steps

1. Read [ADR-0020](../../../docs/adr/0020-legal-research-desk.md), [LEGAL_SAFETY](../../../docs/LEGAL_SAFETY.md), [sources.md](../../../docs/legal-desk/sources.md).
2. Spot-check at least three links in `sources.md`; note DEAD links in the memo.
3. Write or update a memo under `docs/legal-desk/memos/` from `_template.md` (Issue → Sources → Product mapping → Residual risk → Recommended control).
4. Regenerate packet: `bash scripts/generate-legal-review-packet.sh` (or `python3 scripts/agent-run.py` wrapper if present).
5. Confirm `docs/FOUNDER_LEGAL_POSTURE.md` has `Accepted-scope: owner-only+foss` and `Accepted-date: YYYY-MM-DD` before Tier A approve.
6. Remind founder: Tier A closes H-006 / H-022 / H-023 with `--note "residual-risk owner-only+foss …"`; Tier B is **H-006b** (counsel before non-owner billing). See `when-to-get-counsel.md`.

## Do not

- Invent counsel sign-off
- Enable non-owner billing UX
- Skip the honesty banner on memos
