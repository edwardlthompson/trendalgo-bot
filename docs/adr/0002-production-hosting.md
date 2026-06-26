# ADR-0002: Production Hosting — Cost + Puerto Rico Reliability

- **Status:** Accepted (Sprint 0)
- **Date:** 2026-06-25

## Context

Operator in Puerto Rico; utilities/internet unreliable. Live trading must survive local outages. Budget target **< $10/mo**.

## Decision

1. **Production** on external always-on cloud only (Docker Compose, single VPS).
2. **Preferred:** Oracle Cloud Always Free ARM (Ampere A1) — **$0/mo** if eligible (H-004).
3. **Fallback:** Hetzner CX22/CPX11 — **~$5–8/mo**.
4. **Render.com:** dev/staging only; not primary 24/7 bot.
5. **Co-locate** Freqtrade + FastAPI + static Web UI + SQLite on one instance.
6. **AI:** Ollama local dev; VPS rule-based summaries first; paid API behind env flag + caps.
7. **Monitoring:** Telegram + self-hosted health checks; no paid APM.

## Rejected

PR local hardware for production; sleeping free tiers; separate managed DB for MVP.

## Consequences

ARM64 Docker images; `docker-compose.prod.yml`; `scripts/check-hosting-eligibility.sh`.
