"""Extended payment verifier branch coverage."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from trendalgo.billing import payment_verifier as pv
from trendalgo.billing.store import BillingStore


def test_compute_payment_rejects_non_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        pv.compute_payment_sats(0, "u", "2026-06", 100_000)
    with pytest.raises(ValueError, match="positive"):
        pv.compute_stablecoin_atomic(0, "u", "2026-06", "USDC")


def test_enrich_payment_btc_and_stablecoin() -> None:
    btc = pv.enrich_payment_response(
        {
            "id": "p1",
            "asset": "BTC",
            "address": "bc1qtest",
            "amount_btc": 0.001,
            "period": "2026-06",
            "payment_reference": "ref1",
        }
    )
    assert btc["qr_payload"].startswith("bitcoin:")
    usdc = pv.enrich_payment_response(
        {
            "id": "p2",
            "asset": "USDC",
            "address": "0xrecipient",
            "amount_atomic": 12_500_000,
            "token_contract": "0xtoken",
            "chain": "base",
            "period": "2026-06",
            "payment_reference": "ref2",
        }
    )
    assert "ethereum:" in usdc["qr_payload"]


def test_fetch_address_txs_and_find_btc_tx(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = [
        {
            "txid": "tx1",
            "status": {
                "confirmed": True,
                "block_time": int(datetime.now(UTC).timestamp()),
                "confirmations": 2,
            },
            "vout": [{"scriptpubkey_address": "addr", "value": 1000}],
        }
    ]

    class FakeResp:
        def read(self) -> bytes:
            return json.dumps(payload).encode()

        def __enter__(self) -> FakeResp:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(pv.request, "urlopen", lambda _req, timeout=15: FakeResp())
    txs = pv.fetch_address_txs("addr")
    assert len(txs) == 1
    since = datetime.now(UTC) - timedelta(hours=1)
    match = pv.find_matching_btc_tx(txs, address="addr", amount_sats=1000, not_before=since)
    assert match is not None


def test_verify_expired_payment(tmp_path: Path) -> None:
    billing = BillingStore(tmp_path / "billing.db")
    billing.enroll(0.05, "2026-06-draft-1", "install-x")
    intent = pv.create_payment_intent(
        billing,
        period="2026-06",
        amount_usd=5.0,
        install_uuid="install-x",
    )
    with billing._connect() as conn:
        conn.execute(
            "UPDATE settlement_payments SET expires_at = ? WHERE id = ?",
            ((datetime.now(UTC) - timedelta(days=1)).isoformat(), intent["id"]),
        )
    result = pv.verify_pending_payment(billing, intent["id"])
    assert result["status"] == "expired"
    assert result["verified"] is False


def test_verify_on_chain_btc_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    billing = BillingStore(tmp_path / "billing.db")
    billing.enroll(0.05, "2026-06-draft-1", "install-y")
    monkeypatch.setenv("TRENDALGO_BTC_USD_RATE", "100000")
    intent = pv.create_payment_intent(
        billing,
        period="2026-07",
        amount_usd=10.0,
        install_uuid="install-y",
    )
    payment = billing.get_settlement_payment(intent["id"])
    assert payment is not None

    def fake_fetch(_address: str, *, limit: int = 25) -> list[dict]:
        del limit
        return [
            {
                "txid": "onchain-tx",
                "status": {
                    "confirmed": True,
                    "block_time": int(datetime.now(UTC).timestamp()),
                    "confirmations": 3,
                },
                "vout": [
                    {
                        "scriptpubkey_address": payment["address"],
                        "value": int(payment["amount_sats"]),
                    }
                ],
            }
        ]

    monkeypatch.setattr(pv, "fetch_address_txs", fake_fetch)
    result = pv.verify_pending_payment(billing, intent["id"])
    assert result["verified"] is True
    assert result["status"] == "confirmed"


def test_watch_pending_payments(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_PAYMENT_SIMULATE", "1")
    billing = BillingStore(tmp_path / "billing.db")
    billing.enroll(0.05, "2026-06-draft-1", "install-z")
    pv.create_payment_intent(
        billing,
        period="2026-08",
        amount_usd=8.0,
        install_uuid="install-z",
    )
    out = pv.watch_pending_payments(billing)
    assert out["checked"] >= 1
    assert out["confirmed"] >= 1
