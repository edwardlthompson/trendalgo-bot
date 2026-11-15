# Deployment — TrendAlgo Bot

> External VPS only (ADR-0002). **Never** run live/production on local Puerto Rico hardware.

## Hosting decision

| Option | Cost | Notes |
|--------|------|-------|
| Oracle Cloud Always Free ARM | $0 | H-004 eligibility check |
| Hetzner CX22 (fallback) | ~$5–8/mo | If Oracle ineligible |

Run: `bash scripts/check-hosting-eligibility.sh`

## Checklist (H-004)

1. Provision Oracle Always Free ARM **or** Hetzner CX22
2. Confirm account region + ARM quota (`scripts/check-hosting-eligibility.sh`)
3. Multi-arch Docker build on workstation (`docker buildx`)
4. Deploy via `docker-compose.prod.yml` (Sprint 4)
5. Confirm PR disconnect survival — bot runs only on external cloud
6. Document VPS IP in private runbook (not in git)

## Oracle Always Free outline

1. Create Oracle Cloud account; select home region with Ampere availability
2. Create VM.Standard.A1.Flex (4 OCPU, 24 GB RAM)
3. Ubuntu 22.04 ARM64 image
4. Open ports **22** and **443** only. The API is published as `127.0.0.1:8080:8080` — do **not** open host port 8080 on a public interface. Reach it with an SSH tunnel (`ssh -N -L 8080:127.0.0.1:8080 user@vps`) or Tailscale.
5. Install Docker + compose plugin
6. Clone repo; copy `.env` to `/etc/trendalgo/.env`
7. `docker compose -f docker/docker-compose.prod.yml up -d` (Sprint 4)

## Hetzner fallback

CX22 (~€4/mo): same steps; x86_64 images if ARM build unavailable.

## Scripts

- `scripts/check-hosting-eligibility.sh` — DEPLOYMENT.md + fallback path
- `scripts/check-production-cost.sh` — H-012 / H-027 budget ≤ $10/mo
- `scripts/deploy-vps.sh` — Sprint 4 external VPS deploy
- `scripts/backup-restore.sh` — OPS1/OPS2 backup + restore
- `scripts/health-check-cron.sh` — OPS4 cron probe + Telegram alert

## Grok Bot webhook (optional)

Telegram remains the primary channel. The Grok Bot HTTPS webhook is off until `GROKBOT_WEBHOOK_URL` is set. It never delays or replaces Telegram. Copy the URL and sender key from the Grok Bot routine panel into `/etc/trendalgo/.env` (never git). Full schema, filter, and test commands: [`docs/features/grokbot-webhook.md`](features/grokbot-webhook.md).
