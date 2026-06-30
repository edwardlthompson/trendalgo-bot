"""EVM token transfer watcher tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from trendalgo.billing import evm_token_watcher as watcher


def test_pad_topic_address() -> None:
    padded = watcher._pad_topic_address("0xAbCd")
    assert padded.startswith("0x")
    assert padded.endswith("abcd")
    assert len(padded) == 66


def test_rpc_call_success(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"jsonrpc": "2.0", "result": "0x10", "id": 1}

    class FakeResp:
        def read(self) -> bytes:
            return json.dumps(payload).encode()

        def __enter__(self) -> FakeResp:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(watcher.request, "urlopen", lambda _req, timeout=20: FakeResp())
    assert watcher.rpc_call("http://rpc", "eth_blockNumber", []) == "0x10"


def test_rpc_call_error_body(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"jsonrpc": "2.0", "error": {"message": "bad"}, "id": 1}

    class FakeResp:
        def read(self) -> bytes:
            return json.dumps(payload).encode()

        def __enter__(self) -> FakeResp:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(watcher.request, "urlopen", lambda _req, timeout=20: FakeResp())
    with pytest.raises(RuntimeError, match="bad"):
        watcher.rpc_call("http://rpc", "eth_blockNumber", [])


def test_fetch_matching_token_transfer(monkeypatch: pytest.MonkeyPatch) -> None:
    block_time = int(datetime(2026, 6, 1, 12, 0, tzinfo=UTC).timestamp())
    logs = [
        {
            "data": hex(1_000_000),
            "blockNumber": "0x64",
            "transactionHash": "0xabc",
        }
    ]

    def fake_rpc(_url: str, method: str, params: list[Any]) -> Any:
        if method == "eth_getLogs":
            return logs
        if method == "eth_blockNumber":
            return "0x66"
        if method == "eth_getBlockByNumber":
            return {"timestamp": hex(block_time)}
        return None

    monkeypatch.setattr(watcher, "rpc_call", fake_rpc)
    match = watcher.fetch_matching_token_transfer(
        "http://rpc",
        token_contract="0xtoken",
        recipient="0xrecipient",
        amount_atomic=1_000_000,
        from_block=100,
        not_before=datetime(2026, 6, 1, tzinfo=UTC),
    )
    assert match is not None
    assert match["tx_hash"] == "0xabc"
    assert match["confirmations"] >= 1
