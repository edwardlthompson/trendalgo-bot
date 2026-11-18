"""BILL-06: API-key fingerprint + machine id binding, server HWM, seats."""

from __future__ import annotations

from trendalgo.billing.store import BillingStore


def test_fresh_install_same_key_machine_restores_hwm(tmp_path) -> None:
    store = BillingStore(tmp_path / "b.db")
    store.enroll(0.05, "2026-06-draft-1", "uuid-1")
    store.bind_identity(api_key_fingerprint="fp-abc", machine_id="pc-1", seat_count=1)
    store.set_server_hwm(250.0)
    restored = store.restore_hwm_for_identity(api_key_fingerprint="fp-abc", machine_id="pc-1")
    assert restored == 250.0
    assert store.restore_hwm_for_identity(api_key_fingerprint="fp-abc", machine_id="pc-2") is None


def test_second_machine_without_seat_refused(tmp_path) -> None:
    store = BillingStore(tmp_path / "b.db")
    store.enroll(0.05, "2026-06-draft-1", "uuid-1")
    store.bind_identity(api_key_fingerprint="fp-abc", machine_id="pc-1", seat_count=1)
    assert store.seat_allows(active_machines=1) is True
    assert store.seat_allows(active_machines=2) is False
