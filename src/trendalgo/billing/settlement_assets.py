"""Settlement asset catalog — BTC + stablecoins (user-initiated on-chain only)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SettlementAsset:
    asset_id: str
    chain: str
    chain_id: int | None
    decimals: int
    token_contract: str | None
    label: str


BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
BASE_USDT = "0xfde4C96c8593536e31F229EA8f37b2ADa2699bb2"

_CATALOG: dict[str, SettlementAsset] = {
    "BTC": SettlementAsset("BTC", "bitcoin", None, 8, None, "Bitcoin (BTC)"),
    "USDC": SettlementAsset("USDC", "base", 8453, 6, BASE_USDC, "USD Coin (USDC)"),
    "USDT": SettlementAsset("USDT", "base", 8453, 6, BASE_USDT, "Tether (USDT)"),
}


def normalize_asset_id(asset_id: str) -> str:
    key = asset_id.strip().upper()
    if key not in _CATALOG:
        raise ValueError(f"unsupported settlement asset: {asset_id}")
    return key


def get_settlement_asset(asset_id: str) -> SettlementAsset:
    return _CATALOG[normalize_asset_id(asset_id)]


def settlement_btc_address() -> str:
    return os.environ.get("TRENDALGO_SETTLEMENT_ADDRESS", "bc1q-trendalgo-settlement-sample")


def settlement_evm_address() -> str:
    return os.environ.get(
        "TRENDALGO_SETTLEMENT_EVM_ADDRESS",
        "0x000000000000000000000000000000000000dEaD",
    )


def recipient_for_asset(asset: SettlementAsset) -> str:
    if asset.asset_id == "BTC":
        return settlement_btc_address()
    return settlement_evm_address()


def evm_rpc_url(chain: str) -> str:
    if chain == "base":
        return os.environ.get("TRENDALGO_BASE_RPC_URL", "https://mainnet.base.org").strip()
    raise ValueError(f"no RPC configured for chain {chain}")


def token_contract_override(asset_id: str) -> str | None:
    env_key = f"TRENDALGO_{asset_id}_CONTRACT"
    value = os.environ.get(env_key, "").strip()
    return value or None


def contract_for_asset(asset: SettlementAsset) -> str | None:
    override = token_contract_override(asset.asset_id)
    if override:
        return override
    return asset.token_contract


def list_available_assets() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in _CATALOG.values():
        rows.append(
            {
                "asset": asset.asset_id,
                "chain": asset.chain,
                "chain_id": asset.chain_id,
                "label": asset.label,
                "decimals": asset.decimals,
                "token_contract": contract_for_asset(asset),
                "address": recipient_for_asset(asset),
                "enabled": True,
            }
        )
    return rows
