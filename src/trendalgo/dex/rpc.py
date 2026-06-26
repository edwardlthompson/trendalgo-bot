"""RPC URL resolution with failover (S24)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from trendalgo.venues.base import VenueEntry


def rpc_urls(entry: VenueEntry) -> list[str]:
    primary = os.environ.get(entry.rpc_env, "").strip()
    fallback_env = f"{entry.rpc_env}_FALLBACK"
    fallback = os.environ.get(fallback_env, "").strip()
    urls: list[str] = []
    if primary:
        urls.append(primary)
    if fallback and fallback not in urls:
        urls.append(fallback)
    return urls


def rpc_ping(url: str, *, chain_type: str) -> bool:
    if chain_type == "evm":
        payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
    else:
        payload = {"jsonrpc": "2.0", "method": "getHealth", "params": [], "id": 1}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            json.loads(resp.read().decode("utf-8"))
        return True
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return False


def resolve_rpc_url(entry: VenueEntry) -> str | None:
    for url in rpc_urls(entry):
        if rpc_ping(url, chain_type=entry.chain_type):
            return url
    return None


def rpc_status(entry: VenueEntry) -> dict[str, Any]:
    urls = rpc_urls(entry)
    active = resolve_rpc_url(entry) if urls else None
    return {
        "venue": entry.id,
        "primary_configured": bool(urls[0]) if urls else False,
        "fallback_configured": len(urls) > 1,
        "active_url_index": urls.index(active) if active and active in urls else None,
        "reachable": active is not None,
    }
