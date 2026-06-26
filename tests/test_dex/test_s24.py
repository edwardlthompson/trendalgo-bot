"""S24 DEX live swap + ops tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.dex.control import DexVenueControlStore
from trendalgo.dex.gates import validate_live_swap_gates
from trendalgo.dex.load_test import run_dex_ops_validation
from trendalgo.dex.nonce import NonceStore
from trendalgo.dex.router import live_dex_swap
from trendalgo.dex.runner.live import LiveSwapRunner
from trendalgo.dex.signer import sign_swap_payload, signer_configured, signer_fingerprint
from trendalgo.venues.registry import get_venue, load_venue_registry


def _live_env(monkeypatch, tmp_path: Path) -> tuple[DexVenueControlStore, NonceStore]:
    monkeypatch.setenv("DEX_LIVE_TRADING_ACK", "1")
    monkeypatch.setenv("GO_LIVE_APPROVED", "1")
    monkeypatch.setenv("DEX_SIGNER_KEY", "test-signer-key-vps-only")
    monkeypatch.setenv("DEX_MAX_SLIPPAGE_BPS", "100")
    control = DexVenueControlStore(tmp_path / "dex_control.db")
    control.approve_go_live("base")
    return control, NonceStore(tmp_path / "nonces.json")


def test_registry_v4_live_phase() -> None:
    registry = load_venue_registry()
    assert registry.version == 4
    assert registry.dex_live_phase == 1
    base = get_venue("base")
    assert base.trading_enabled is True
    assert get_venue("ethereum").trading_enabled is False


def test_signer_never_exposes_raw_key(monkeypatch) -> None:
    monkeypatch.setenv("DEX_SIGNER_KEY", "super-secret-key")
    assert signer_configured() is True
    fp = signer_fingerprint()
    assert fp is not None
    assert "super-secret" not in fp
    tx = sign_swap_payload("base:ETH:USDC:1:0:50")
    assert tx.startswith("0x")
    assert "super-secret" not in tx


def test_live_swap_gates(tmp_path: Path, monkeypatch) -> None:
    control = DexVenueControlStore(tmp_path / "dex_control.db")
    with pytest.raises(ValueError, match="H-036"):
        validate_live_swap_gates("base", control, slippage_bps=50)
    monkeypatch.setenv("DEX_LIVE_TRADING_ACK", "1")
    with pytest.raises(ValueError, match="GO_LIVE_APPROVED"):
        validate_live_swap_gates("base", control, slippage_bps=50)
    monkeypatch.setenv("GO_LIVE_APPROVED", "1")
    with pytest.raises(ValueError, match="DEX_SIGNER_KEY"):
        validate_live_swap_gates("base", control, slippage_bps=50)


def test_live_swap_base_venue(tmp_path: Path, monkeypatch) -> None:
    control, nonce_store = _live_env(monkeypatch, tmp_path)
    result = live_dex_swap(
        "base",
        "ETH",
        "USDC",
        0.25,
        control=control,
        nonce_store=nonce_store,
        slippage_bps=30,
    )
    assert result["mode"] == "live"
    assert result["tx_broadcast"] is True
    assert result["tx_hash"].startswith("0x")
    assert result["signer_fingerprint"]
    assert result["nonce"] == 0


def test_live_swap_blocked_non_trading_venue(tmp_path: Path, monkeypatch) -> None:
    control, nonce_store = _live_env(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="trading not enabled"):
        live_dex_swap(
            "ethereum",
            "ETH",
            "USDC",
            1.0,
            control=control,
            nonce_store=nonce_store,
        )


def test_live_runner_no_transfer_helpers() -> None:
    assert not hasattr(LiveSwapRunner, "transfer")
    assert not hasattr(LiveSwapRunner, "withdraw")


def test_dex_ops_validation() -> None:
    result = run_dex_ops_validation()
    assert result["ok"] is True
    assert result["wallet_sync"]["synced_count"] >= 3


def test_s24_api_routes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    _live_env(monkeypatch, tmp_path)
    from fastapi.testclient import TestClient

    from trendalgo.api.app import create_app

    client = TestClient(create_app())
    status = client.get("/api/v1/platform/dex/status/full")
    assert status.status_code == 200
    body = status.json()
    assert body["dex_live_phase"] == 1
    assert "base" in body["live_trading_venues"]

    go_live = client.post("/api/v1/platform/dex/venues/base/go-live")
    assert go_live.status_code == 200

    live = client.post(
        "/api/v1/platform/dex/live",
        json={
            "chain": "base",
            "sell_token": "ETH",
            "buy_token": "USDC",
            "sell_amount": 0.1,
            "slippage_bps": 25,
        },
    )
    assert live.status_code == 200
    assert live.json()["mode"] == "live"

    ops = client.get("/api/v1/platform/dex/ops-validation")
    assert ops.status_code == 200
    assert ops.json()["ok"] is True
