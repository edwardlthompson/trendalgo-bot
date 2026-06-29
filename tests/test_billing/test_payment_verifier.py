"""On-chain payment verification tests (Option B)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from trendalgo.billing.license_gate import check_license_gate, licensed_until_for_period
from trendalgo.billing.payment_verifier import (
    compute_payment_sats,
    create_payment_intent,
    find_matching_tx,
    verify_pending_payment,
)
from trendalgo.billing.store import BillingStore


@pytest.fixture(autouse=True)
def _btc_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_BTC_USD_RATE", "100000")


def test_compute_payment_sats_unique() -> None:
    sats_a, _, ref_a, _ = compute_payment_sats(25.0, "uuid-a", "2026-06", 100_000.0)
    sats_b, _, ref_b, _ = compute_payment_sats(25.0, "uuid-b", "2026-06", 100_000.0)
    assert sats_a != sats_b or ref_a != ref_b
    assert sats_a >= 546


def test_find_matching_tx() -> None:
    since = datetime.now(UTC) - timedelta(hours=1)
    txs = [
        {
            "txid": "abc123",
            "status": {
                "confirmed": True,
                "block_time": int(datetime.now(UTC).timestamp()),
                "confirmations": 2,
            },
            "vout": [{"scriptpubkey_address": "bc1q-test", "value": 25050}],
        }
    ]
    match = find_matching_tx(txs, address="bc1q-test", amount_sats=25050, not_before=since)
    assert match is not None
    assert match["tx_hash"] == "abc123"


def test_simulated_payment_unlocks_license(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_PAYMENT_SIMULATE", "1")
    billing = BillingStore(tmp_path / "billing.db")
    billing.enroll(0.05, "2026-06-draft-1", "install-1")
    intent = create_payment_intent(
        billing,
        period="2026-06",
        amount_usd=12.5,
        install_uuid="install-1",
    )
    result = verify_pending_payment(billing, intent["id"])
    assert result["verified"] is True
    assert result["status"] == "confirmed"
    status = billing.get_license_status()
    assert status["suspended"] == 0
    assert status["grace_day"] == 0
    assert status["licensed_until"] == licensed_until_for_period("2026-06")
    ok, reason = check_license_gate(billing.get_enrollment(), status, dry_run=False)
    assert ok is True
    assert reason == "licensed_until"


def test_simulated_usdc_payment_unlocks_license(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_PAYMENT_SIMULATE", "1")
    billing = BillingStore(tmp_path / "billing.db")
    billing.enroll(0.05, "2026-06-draft-1", "install-usdc")
    intent = create_payment_intent(
        billing,
        period="2026-06",
        amount_usd=12.5,
        install_uuid="install-usdc",
        asset_id="USDC",
    )
    assert intent["asset"] == "USDC"
    assert intent["chain"] == "base"
    assert intent["amount_to_send"] > 12.5
    result = verify_pending_payment(billing, intent["payment_id"])
    assert result["verified"] is True
    assert billing.get_license_status()["licensed_until"] == licensed_until_for_period("2026-06")


def test_list_available_assets() -> None:
    from trendalgo.billing.settlement_assets import list_available_assets

    assets = list_available_assets()
    ids = {row["asset"] for row in assets}
    assert {"BTC", "USDC", "USDT"}.issubset(ids)


def test_payment_intent_idempotent_for_period(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_PAYMENT_SIMULATE", "1")
    billing = BillingStore(tmp_path / "billing.db")
    billing.enroll(0.05, "2026-06-draft-1", "install-2")
    first = create_payment_intent(
        billing,
        period="2026-06",
        amount_usd=10.0,
        install_uuid="install-2",
    )
    second = create_payment_intent(
        billing,
        period="2026-06",
        amount_usd=10.0,
        install_uuid="install-2",
    )
    assert first["id"] != second["id"]
    pending = billing.list_pending_settlement_payments()
    assert len(pending) == 1
