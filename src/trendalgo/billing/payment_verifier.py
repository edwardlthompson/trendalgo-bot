"""On-chain settlement verification — BTC + stablecoins (Option B)."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib import error, request

from trendalgo.billing.btc_quote import fetch_btc_usd
from trendalgo.billing.evm_token_watcher import (
    fetch_latest_block_number,
    fetch_matching_token_transfer,
)
from trendalgo.billing.license_gate import clear_grace, licensed_until_for_period
from trendalgo.billing.onchain_receipts import issue_fee_receipt
from trendalgo.billing.settlement_assets import (
    SettlementAsset,
    contract_for_asset,
    evm_rpc_url,
    get_settlement_asset,
    normalize_asset_id,
    recipient_for_asset,
)
from trendalgo.billing.store import BillingStore

MIN_CONFIRMATIONS = 1
PAYMENT_EXPIRY_DAYS = 14
SATS_FINGERPRINT_MOD = 10_000
STABLE_FINGERPRINT_MOD = 10_000


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _payment_digest(install_uuid: str, period: str, amount_usd: float, asset_id: str) -> str:
    return hashlib.sha256(
        f"{install_uuid}:{period}:{amount_usd:.2f}:{asset_id}".encode()
    ).hexdigest()


def compute_payment_sats(
    amount_usd: float, install_uuid: str, period: str, btc_usd: float
) -> tuple[int, float, str, str]:
    if amount_usd <= 0:
        raise ValueError("amount_usd must be positive")
    digest = _payment_digest(install_uuid, period, amount_usd, "BTC")
    base_sats = max(546, int(round(amount_usd / btc_usd * 100_000_000)))
    fingerprint = int(digest[:8], 16) % SATS_FINGERPRINT_MOD
    amount_sats = base_sats + fingerprint
    amount_btc = round(amount_sats / 100_000_000, 8)
    return amount_sats, amount_btc, digest[:12], f"rcpt-{digest[:16]}"


def compute_stablecoin_atomic(
    amount_usd: float, install_uuid: str, period: str, asset_id: str
) -> tuple[int, float, str, str]:
    if amount_usd <= 0:
        raise ValueError("amount_usd must be positive")
    digest = _payment_digest(install_uuid, period, amount_usd, asset_id)
    base_units = max(1, int(round(amount_usd * 1_000_000)))
    fingerprint = int(digest[:8], 16) % STABLE_FINGERPRINT_MOD
    amount_atomic = base_units + fingerprint
    amount_display = round(amount_atomic / 1_000_000, 6)
    return amount_atomic, amount_display, digest[:12], f"rcpt-{digest[:16]}"


def esplora_base_url() -> str:
    return os.environ.get("TRENDALGO_ESPLORA_URL", "https://blockstream.info/api").rstrip("/")


def fetch_address_txs(address: str, *, limit: int = 25) -> list[dict[str, Any]]:
    url = f"{esplora_base_url()}/address/{address}/txs"
    req = request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "TrendAlgo/1.0"}
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("Unable to reach block explorer") from exc
    if not isinstance(data, list):
        return []
    return data[:limit]


def _output_sats(vout: dict[str, Any]) -> int:
    value = vout.get("value")
    if isinstance(value, int):
        return value
    if value is None:
        return 0
    return int(round(float(value) * 100_000_000))


def find_matching_btc_tx(
    txs: list[dict[str, Any]],
    *,
    address: str,
    amount_sats: int,
    not_before: datetime,
    min_confirmations: int = MIN_CONFIRMATIONS,
) -> dict[str, Any] | None:
    cutoff = int(not_before.timestamp())
    for tx in txs:
        status = tx.get("status") or {}
        if not status.get("confirmed"):
            continue
        block_time = int(status.get("block_time") or 0)
        if block_time and block_time < cutoff:
            continue
        confs = int(status.get("confirmations") or 0)
        if confs < min_confirmations:
            continue
        txid = str(tx.get("txid") or "")
        for vout in tx.get("vout") or []:
            if str(vout.get("scriptpubkey_address") or "") != address:
                continue
            if _output_sats(vout) == amount_sats:
                return {"tx_hash": txid, "confirmations": confs, "block_time": block_time}
    return None


def build_btc_qr_payload(
    address: str, amount_btc: float, period: str, payment_reference: str
) -> str:
    label = f"TrendAlgo-{period}-{payment_reference}"
    return f"bitcoin:{address}?amount={amount_btc:.8f}&label={label}"


def build_stablecoin_qr_payload(
    asset: SettlementAsset,
    token_contract: str,
    recipient: str,
    amount_atomic: int,
    period: str,
    payment_reference: str,
) -> str:
    label = f"TrendAlgo-{period}-{payment_reference}"
    chain_id = asset.chain_id or 8453
    return (
        f"ethereum:{token_contract}@{chain_id}/transfer"
        f"?address={recipient}&uint256={amount_atomic}&label={label}"
    )


def amount_to_send(payment: dict[str, Any]) -> float:
    asset = str(payment.get("asset") or "BTC")
    if asset == "BTC":
        return float(payment.get("amount_btc") or 0)
    atomic = int(payment.get("amount_atomic") or 0)
    return round(atomic / 1_000_000, 6)


def enrich_payment_response(payment: dict[str, Any]) -> dict[str, Any]:
    asset_id = str(payment.get("asset") or "BTC")
    asset = get_settlement_asset(asset_id)
    to_send = amount_to_send(payment)
    if asset_id == "BTC":
        qr = build_btc_qr_payload(
            str(payment["address"]),
            float(payment.get("amount_btc") or to_send),
            str(payment["period"]),
            str(payment["payment_reference"]),
        )
        instructions = (
            f"Send exactly {to_send:.8f} BTC to the address below. "
            f"Reference: {payment['payment_reference']}. "
            "License unlocks automatically after confirmation."
        )
    else:
        token = str(payment.get("token_contract") or contract_for_asset(asset) or "")
        qr = build_stablecoin_qr_payload(
            asset,
            token,
            str(payment["address"]),
            int(payment.get("amount_atomic") or 0),
            str(payment["period"]),
            str(payment["payment_reference"]),
        )
        instructions = (
            f"Send exactly {to_send:.6f} {asset_id} on {asset.chain.title()} to the address below. "
            f"Reference: {payment['payment_reference']}. "
            "License unlocks automatically after on-chain confirmation."
        )
    return {
        **payment,
        "payment_id": str(payment.get("id") or payment.get("payment_id") or ""),
        "amount_to_send": to_send,
        "asset": asset_id,
        "chain": str(payment.get("chain") or asset.chain),
        "chain_id": payment.get("chain_id")
        if payment.get("chain_id") is not None
        else asset.chain_id,
        "qr_payload": qr,
        "payment_instructions": instructions,
        "auto_verify": True,
        "min_confirmations": MIN_CONFIRMATIONS,
        "grace_period_days": 7,
        "user_initiated_only": True,
        "auto_withdraw": False,
        "disclaimer": "Pay from your own wallet. TrendAlgo never holds withdrawal keys.",
    }


def create_payment_intent(
    billing: BillingStore,
    *,
    period: str,
    amount_usd: float,
    install_uuid: str,
    asset_id: str = "BTC",
) -> dict[str, Any]:
    if amount_usd <= 0:
        raise ValueError("No license fee due for this period")
    asset_key = normalize_asset_id(asset_id)
    asset = get_settlement_asset(asset_key)
    address = recipient_for_asset(asset)
    now = _utc_now()
    payment_id = f"pay-{uuid.uuid4().hex[:12]}"
    expires_at = now + timedelta(days=PAYMENT_EXPIRY_DAYS)
    billing.supersede_pending_payments(period, install_uuid)

    if asset_key == "BTC":
        btc_usd = fetch_btc_usd()
        amount_sats, amount_btc, payment_reference, receipt_id = compute_payment_sats(
            amount_usd, install_uuid, period, btc_usd
        )
        amount_atomic = amount_sats
        token_contract = None
        watch_from_block = None
        chain_id = None
        receipt = issue_fee_receipt(period, amount_usd, wallet=address, chain="bitcoin")
        store_amount_btc = amount_btc
    else:
        btc_usd = None
        token_contract = contract_for_asset(asset)
        if not token_contract:
            raise ValueError(f"token contract not configured for {asset_key}")
        amount_atomic, _amount_display, payment_reference, receipt_id = compute_stablecoin_atomic(
            amount_usd, install_uuid, period, asset_key
        )
        amount_sats = 0
        store_amount_btc = 0.0
        if os.environ.get("TRENDALGO_PAYMENT_SIMULATE") == "1":
            watch_from_block = 1
        else:
            rpc = evm_rpc_url(asset.chain)
            watch_from_block = fetch_latest_block_number(rpc)
        chain_id = asset.chain_id
        receipt = issue_fee_receipt(period, amount_usd, wallet=address, chain=asset.chain)

    payment = billing.create_settlement_payment(
        payment_id=payment_id,
        period=period,
        install_uuid=install_uuid,
        amount_usd=amount_usd,
        amount_sats=amount_sats,
        amount_btc=store_amount_btc,
        amount_atomic=amount_atomic,
        asset=asset_key,
        chain=asset.chain,
        chain_id=chain_id,
        token_contract=token_contract,
        watch_from_block=watch_from_block,
        payment_reference=payment_reference,
        receipt_id=receipt_id,
        verification_hash=receipt["verification_hash"],
        address=address,
        created_at=_iso(now),
        expires_at=_iso(expires_at),
    )
    enriched = enrich_payment_response(payment)
    if btc_usd is not None:
        enriched["btc_usd_rate"] = round(btc_usd, 2)
    return enriched


def activate_license(
    billing: BillingStore, payment: dict[str, Any], tx_hash: str, confirmations: int
) -> dict[str, Any]:
    licensed_until = licensed_until_for_period(str(payment["period"]))
    confirmed_at = _iso(_utc_now())
    billing.confirm_settlement_payment(
        str(payment["id"]),
        tx_hash=tx_hash,
        confirmations=confirmations,
        licensed_until=licensed_until,
        confirmed_at=confirmed_at,
    )
    status = clear_grace(billing.get_license_status())
    status["licensed_until"] = licensed_until
    status["last_payment_id"] = payment["id"]
    status["last_tx_hash"] = tx_hash
    billing.update_license_status(status)
    return billing.get_license_status()


def _verify_on_chain(payment: dict[str, Any], not_before: datetime) -> dict[str, Any] | None:
    asset = str(payment.get("asset") or "BTC")
    if asset == "BTC":
        txs = fetch_address_txs(str(payment["address"]))
        return find_matching_btc_tx(
            txs,
            address=str(payment["address"]),
            amount_sats=int(payment["amount_sats"]),
            not_before=not_before,
        )
    rpc = evm_rpc_url(str(payment.get("chain") or "base"))
    from_block = int(payment.get("watch_from_block") or 0)
    token = str(payment.get("token_contract") or "")
    if not token or from_block <= 0:
        return None
    return fetch_matching_token_transfer(
        rpc,
        token_contract=token,
        recipient=str(payment["address"]),
        amount_atomic=int(payment.get("amount_atomic") or 0),
        from_block=from_block,
        not_before=not_before,
    )


def verify_pending_payment(
    billing: BillingStore,
    payment_id: str,
    *,
    simulate_tx_hash: str | None = None,
) -> dict[str, Any]:
    payment = billing.get_settlement_payment(payment_id)
    if payment is None:
        raise ValueError("payment not found")
    if payment["status"] == "confirmed":
        return {
            "payment": enrich_payment_response(payment),
            "verified": True,
            "status": "confirmed",
        }
    if payment["status"] != "pending":
        return {
            "payment": enrich_payment_response(payment),
            "verified": False,
            "status": payment["status"],
        }

    expires = datetime.fromisoformat(str(payment["expires_at"]))
    if _utc_now() > expires:
        billing.expire_settlement_payment(payment_id)
        expired = billing.get_settlement_payment(payment_id)
        return {
            "payment": enrich_payment_response(expired or payment),
            "verified": False,
            "status": "expired",
        }

    if simulate_tx_hash or os.environ.get("TRENDALGO_PAYMENT_SIMULATE") == "1":
        tx_hash = simulate_tx_hash or f"sim-{payment_id}"
        status = activate_license(billing, payment, tx_hash, MIN_CONFIRMATIONS)
        confirmed = billing.get_settlement_payment(payment_id)
        return {
            "payment": enrich_payment_response(confirmed or payment),
            "verified": True,
            "status": "confirmed",
            "license_status": status,
        }

    not_before = datetime.fromisoformat(str(payment["created_at"]))
    match = _verify_on_chain(payment, not_before)
    if match is None:
        return {
            "payment": enrich_payment_response(payment),
            "verified": False,
            "status": "pending",
            "watching": True,
        }

    status = activate_license(
        billing,
        payment,
        str(match["tx_hash"]),
        int(match["confirmations"]),
    )
    confirmed = billing.get_settlement_payment(payment_id)
    return {
        "payment": enrich_payment_response(confirmed or payment),
        "verified": True,
        "status": "confirmed",
        "license_status": status,
    }


def watch_pending_payments(billing: BillingStore) -> dict[str, Any]:
    pending = billing.list_pending_settlement_payments()
    confirmed = 0
    for row in pending:
        result = verify_pending_payment(billing, str(row["id"]))
        if result.get("verified"):
            confirmed += 1
    return {"checked": len(pending), "confirmed": confirmed}


# Backward-compatible alias for tests
find_matching_tx = find_matching_btc_tx
build_qr_payload = build_btc_qr_payload
