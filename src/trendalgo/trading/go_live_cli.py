"""Owner-signed per-exchange go-live (H2, H3). `scripts/go-live-gate.sh --approve` runs this.

The approval is sent to the host as an owner-signed command. The audit line is written only
after the host accepts it, so a refused or unreachable host leaves no approval record.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib import error, request

from trendalgo.exchanges.registry import list_trading_exchanges
from trendalgo.trading.signed_command import OWNER_ID_ENV, OWNER_SECRET_ENV, sign_request

AUDIT_PATH = Path("data/audit/go-live.jsonl")
DEFAULT_HOST_URL = "http://127.0.0.1:8000"


def go_live_path(exchange_id: str) -> str:
    return f"/api/v1/trading/exchanges/{exchange_id}/go-live"


def signed_headers(
    exchange_id: str, *, owner_id: str, secret: str, timestamp: int, nonce: str
) -> dict[str, str]:
    return sign_request(
        method="POST",
        path=go_live_path(exchange_id),
        body=b"",
        owner_id=owner_id,
        secret=secret,
        timestamp=timestamp,
        nonce=nonce,
    )


def post_go_live(host_url: str, exchange_id: str, *, owner_id: str, secret: str) -> int:
    """Send one signed approval. Returns the HTTP status; 0 when the host is unreachable."""
    headers = signed_headers(
        exchange_id,
        owner_id=owner_id,
        secret=secret,
        timestamp=int(datetime.now(UTC).timestamp()),
        nonce=secrets.token_urlsafe(24),
    )
    req = request.Request(
        host_url.rstrip("/") + go_live_path(exchange_id),
        data=b"",
        method="POST",
        headers=headers,
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            return int(resp.status)
    except error.HTTPError as exc:
        return int(exc.code)
    except (error.URLError, TimeoutError):
        return 0


def append_audit(exchange_id: str) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "install_uuid": str(uuid.uuid4()),
        "approved_at": datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gate": "H-010/H-028",
        "exchange": exchange_id,
        "signed": True,
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def _targets(exchange: str) -> list[str]:
    if exchange == "all":
        return [entry.id for entry in list_trading_exchanges()]
    return [exchange]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Owner-signed go-live approval (H2/H3).")
    parser.add_argument("--exchange", required=True, help="exchange id, or 'all'")
    parser.add_argument(
        "--host-url", default=os.environ.get("TRENDALGO_HOST_URL", DEFAULT_HOST_URL)
    )
    args = parser.parse_args(argv)
    owner_id = os.environ.get(OWNER_ID_ENV)
    secret = os.environ.get(OWNER_SECRET_ENV)
    if not owner_id or not secret:
        print(f"FAIL set {OWNER_ID_ENV} and {OWNER_SECRET_ENV} before approving")
        return 2
    for exchange_id in _targets(args.exchange):
        status = post_go_live(args.host_url, exchange_id, owner_id=owner_id, secret=secret)
        if status != 200:
            print(
                f"FAIL {exchange_id}: host answered {status or 'no response'}; no audit line written"
            )
            return 1
        append_audit(exchange_id)
        print(f"OK   {exchange_id}: approved by owner-signed command (logged to {AUDIT_PATH})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
