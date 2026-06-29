"""ERC-20 stablecoin transfer watcher via JSON-RPC (Base / EVM)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from urllib import error, request

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _pad_topic_address(address: str) -> str:
    raw = address.lower().removeprefix("0x")
    return "0x" + raw.zfill(64)


def rpc_call(rpc_url: str, method: str, params: list[Any]) -> Any:
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = request.Request(
        rpc_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "TrendAlgo/1.0"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=20) as resp:
            body: dict[str, Any] = json.loads(resp.read().decode())
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Unable to reach EVM RPC") from exc
    if body.get("error"):
        raise RuntimeError(str(body["error"]))
    return body.get("result")


def fetch_latest_block_number(rpc_url: str) -> int:
    result = rpc_call(rpc_url, "eth_blockNumber", [])
    return int(str(result), 16)


def fetch_block_timestamp(rpc_url: str, block_number: int) -> int:
    result = rpc_call(rpc_url, "eth_getBlockByNumber", [hex(block_number), False])
    if not isinstance(result, dict):
        return 0
    return int(str(result.get("timestamp") or "0x0"), 16)


def fetch_matching_token_transfer(
    rpc_url: str,
    *,
    token_contract: str,
    recipient: str,
    amount_atomic: int,
    from_block: int,
    not_before: datetime,
    min_confirmations: int = 1,
) -> dict[str, Any] | None:
    cutoff = int(not_before.timestamp())
    logs = rpc_call(
        rpc_url,
        "eth_getLogs",
        [
            {
                "fromBlock": hex(from_block),
                "toBlock": "latest",
                "address": token_contract,
                "topics": [TRANSFER_TOPIC, None, _pad_topic_address(recipient)],
            }
        ],
    )
    if not isinstance(logs, list):
        return None

    latest = fetch_latest_block_number(rpc_url)
    for entry in logs:
        if not isinstance(entry, dict):
            continue
        data_hex = str(entry.get("data") or "0x0")
        value = int(data_hex, 16)
        if value != amount_atomic:
            continue
        block_hex = entry.get("blockNumber")
        if not block_hex:
            continue
        block_num = int(str(block_hex), 16)
        block_time = fetch_block_timestamp(rpc_url, block_num)
        if block_time and block_time < cutoff:
            continue
        confirmations = max(0, latest - block_num + 1)
        if confirmations < min_confirmations:
            continue
        tx_hash = str(entry.get("transactionHash") or "")
        return {"tx_hash": tx_hash, "confirmations": confirmations, "block_time": block_time}
    return None
