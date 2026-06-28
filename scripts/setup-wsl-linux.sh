#!/usr/bin/env bash
# Dev dependencies inside WSL for TrendAlgo repo bash gates.
# Invoked by scripts/setup-wsl.ps1 — do not require interactive prompts.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

echo "=== setup-wsl-linux: apt packages ==="
apt-get update -qq
apt-get install -y -qq \
  bash \
  ca-certificates \
  curl \
  dos2unix \
  git \
  jq \
  python3 \
  python3-pip \
  python3-venv \
  build-essential

if ! command -v uv >/dev/null 2>&1; then
  echo "=== installing uv ==="
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # shellcheck disable=SC1091
  [ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"
fi

REPO_WIN="${TRENDALGO_REPO_WIN:-/mnt/c/Users/edwar/trendalgo-bot}"
if [ -d "$REPO_WIN" ]; then
  echo "=== normalizing script line endings (CRLF -> LF) ==="
  find "$REPO_WIN/scripts" -maxdepth 1 -name '*.sh' -print0 2>/dev/null \
    | xargs -0 -r dos2unix -q 2>/dev/null || true
fi

echo "=== setup-wsl-linux: done ==="
echo "Run gates: wsl -d Ubuntu-24.04 -- bash -lc 'cd $REPO_WIN && bash scripts/watch-agent-gates.sh --once --autofix'"
