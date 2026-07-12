# Local Development & Preview

> **Purpose:** Run the PWA + API on your machine with dry-run sample data — no exchange keys required.
> **Related:** [`docs/EXCHANGE_ROADMAP.md`](EXCHANGE_ROADMAP.md) · [`BUILD_PLAN.md`](../BUILD_PLAN.md) § Local Preview Protocol

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12+ | `uv sync --extra dev --extra ta` from repo root |
| Node.js | 20+ | For `examples/web` |
| npm | 10+ | `cd examples/web && npm ci` |
On Windows, use **PowerShell** scripts (`scripts/dev-local.ps1`). Bash scripts work in WSL or Git Bash.

## Three preview tiers

| Tier | When | What you see |
|------|------|--------------|
| **L1 — Dev hot reload** | Daily UI/API work | Vite HMR + live API on port 8000 |
| **L2 — Production build** | Before PR / sprint sign-off | Built PWA + API (no HMR) |
| **L3 — Docker stack** | Parity with prod compose | API in container (`docker compose --profile full`) |
## L1 — Quick start (recommended)

### Windows (PowerShell)

```powershell
.\scripts\dev-local.ps1

```

### Linux / macOS / WSL

```bash
bash scripts/dev-local.sh

```

Then open **http://localhost:5173** (Vite proxies `/api` → `http://127.0.0.1:8000`).

### Manual (both platforms)

```bash
# Terminal 1 — API
cp .env.example .env   # if missing
export TRENDALGO_DATA_DIR=./data/dev   # PowerShell: $env:TRENDALGO_DATA_DIR = "./data/dev"
python -m trendalgo.api.main

# Terminal 2 — Web
cd examples/web && npm run dev

```

## L2 — Production build preview

```powershell
.\scripts\preview-local.ps1

```

Or manually:

```bash
cd examples/web && npm run build && npm run preview
# Separate terminal: python -m trendalgo.api.main

```

Preview server defaults to port **4173**; API stays on **8000**.

## L3 — Docker (optional)

```bash
docker compose -f docker/docker-compose.yml --profile full up trendalgo-api

```

API is exposed on **8000** (aligned with Vite proxy). Native CCXT API only — no Freqtrade service in compose.

## Environment

| Variable | Default (local) | Purpose |
|----------|-----------------|--------|
| `TRENDALGO_MODE` | `dry-run` | No live orders |
| `TRENDALGO_DATA_DIR` | `./data/dev` | Isolated SQLite + fixtures |
| `TRENDALGO_API_PORT` | `8000` | API listen port |
| `DATABASE_URL` | `sqlite:///./data/dev/trendalgo.db` | Override via `.env` |
| `TRENDALGO_BOT_SCHEDULER_ENABLED` | `1` | Background bot candle ticks |
| `TRENDALGO_BOT_TICK_SECONDS` | `60` | Interval between bot ticks |
| `TV_EXECUTION_ACK` | unset/`0` | Opt-in TradingView order bridge |
Copy [`.env.example`](../.env.example) → `.env`. **Never commit `.env`.**

Exchange keys are optional for L1 — portfolio sync returns dry-run sample data when keys are absent. Telegram ingress needs `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` (returns 503 when unset).

## Manual verification checklist

Use before S13+ commits touching `examples/web/` or `src/trendalgo/api/`:

- [ ] Portfolio overview loads (net worth, holdings)
- [ ] Nav: dashboard, strategies, billing, scanner, export
- [ ] API health widget shows online
- [ ] Sync button returns dry-run sample (no keys)
- [ ] Theme toggle / mobile nav
- [ ] After S13+: multi-exchange accounts panel shows registry venues
- [ ] After S15+: bot dashboard shows `engine=native` badge

Sign off in founder gates: `python scripts/founder_gate.py approve H-034 --note "L1 preview OK"`

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 8000 in use | Set `TRENDALGO_API_PORT=8001` and update Vite proxy in `examples/web/vite.config.ts` |
| `npm run dev` fails | Run `npm ci` in `examples/web` |
| API import errors | `pip install -e .` from repo root |
| Bash gates fail on Windows | Use `python scripts/founder_gate.py` (see KB-001) |
| Blank portfolio | Ensure `TRENDALGO_DATA_DIR` exists; API logs should show dry-run mode |
## Gate

**H-034 (soft):** Local preview completed for current sprint. Preflight checks this doc + dev scripts exist; human confirms L1/L2 run.
