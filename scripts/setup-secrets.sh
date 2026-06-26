#!/usr/bin/env bash
# Interactive .env secret setup (H-008, H-011). Never echoes values.
# Usage: scripts/setup-secrets.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ENV_FILE="$ROOT/.env"
EXAMPLE="$ROOT/.env.example"

echo "=== setup-secrets (values are never printed) ==="
if [ ! -f "$EXAMPLE" ]; then
  echo "FAIL missing .env.example"
  exit 1
fi

python3 - "$ENV_FILE" "$EXAMPLE" <<'PY'
import getpass
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
example = Path(sys.argv[2]).read_text(encoding="utf-8")
existing = env_path.read_text(encoding="utf-8") if env_path.exists() else example

prompts = {
    "TELEGRAM_BOT_TOKEN": "Telegram bot token (H-008, optional — Enter to skip)",
    "TELEGRAM_CHAT_ID": "Telegram chat ID (H-008, optional — Enter to skip)",
    "KRAKEN_API_KEY": "Kraken read-only API key (H-011, optional — Enter to skip)",
    "KRAKEN_API_SECRET": "Kraken read-only API secret (H-011, optional — Enter to skip)",
}

lines = existing.splitlines()
keys = {ln.split("=", 1)[0].strip() for ln in lines if "=" in ln and not ln.strip().startswith("#")}

for key, label in prompts.items():
    if key in keys and any(ln.startswith(f"{key}=") and not ln.endswith("=") for ln in lines if "=" in ln):
        continue
    val = getpass.getpass(f"{label}: ")
    if not val:
        continue
    replaced = False
    new_lines = []
    for ln in lines:
        if ln.startswith(f"{key}="):
            new_lines.append(f"{key}={val}")
            replaced = True
        else:
            new_lines.append(ln)
    if not replaced:
        new_lines.append(f"{key}={val}")
    lines = new_lines

env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
print("OK   .env updated (secrets not displayed)")
PY

echo "Never commit .env — gitleaks pre-commit enforced"
