"""Composition root for the host API (ADR-0016).

Run with `uvicorn trendalgo.botd.service:build_app --factory`. Issue a pairing code from the host
console with `python -m trendalgo.botd.service pair`. Environment: TRENDALGO_OWNER_ID and
TRENDALGO_OWNER_SECRET (both required; the host refuses to start without them), and optionally
TRENDALGO_BOTD_DIR (default data/botd).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI

from trendalgo.botd.api import create_botd_app
from trendalgo.botd.host_store import HostStore
from trendalgo.botd.pairing import PairingCodes
from trendalgo.trading.signed_command import now_seconds, owner_config

BOTD_DIR_ENV = "TRENDALGO_BOTD_DIR"
DEFAULT_BOTD_DIR = Path("data") / "botd"


def _root() -> Path:
    return Path(os.environ.get(BOTD_DIR_ENV) or DEFAULT_BOTD_DIR)


def build_app() -> FastAPI:
    secret, owner_id = owner_config()
    if not owner_id or not secret:
        raise RuntimeError("TRENDALGO_OWNER_ID and TRENDALGO_OWNER_SECRET must be set")
    root = _root()
    return create_botd_app(
        store=HostStore(root / "host.db"),
        host_owner_id=owner_id,
        nonce_db=root / "nonces.db",
        secret_provider=lambda: owner_config()[0],
        secrets_root=root,
    )


def main(argv: list[str]) -> int:
    if argv != ["pair"]:
        print("usage: python -m trendalgo.botd.service pair", file=sys.stderr)
        return 2
    code = PairingCodes(HostStore(_root() / "host.db")).issue(now_seconds())
    print(f"pairing code (valid 10 minutes, use once): {code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
