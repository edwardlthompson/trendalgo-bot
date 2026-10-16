"""ADR-0017 seams: owner boundary, fills ledger, plan bundle header, and the Entitlements port."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from trendalgo.billing.license_gate import LicenseEntitlements
from trendalgo.botd.bundle import bundle_hash, verify_bundle
from trendalgo.botd.fills import FillsLedger
from trendalgo.botd.owner import ForeignOwnerError, assert_owner

HOST = "owner-host-1"


def test_the_host_owner_passes_and_a_foreign_owner_is_refused() -> None:
    assert_owner(HOST, HOST)
    with pytest.raises(ForeignOwnerError, match="foreign"):
        assert_owner("owner-other", HOST)


def test_a_missing_owner_on_either_side_fails_closed() -> None:
    with pytest.raises(ForeignOwnerError, match="missing"):
        assert_owner(None, HOST)
    with pytest.raises(ForeignOwnerError, match="missing"):
        assert_owner(HOST, "")


def _ledger(tmp_path: Path) -> FillsLedger:
    return FillsLedger(tmp_path / "fills.db", host_owner_id=HOST)


def _record(ledger: FillsLedger, **overrides: Any) -> int:
    fields: dict[str, Any] = {
        "owner_id": HOST,
        "live": True,
        "plan_version": 3,
        "bundle_hash": "abc123",
        "pair": "BTC/USD",
        "side": "buy",
        "amount": 0.0005,
        "price": 50_000.0,
        "filled_at": "2026-10-10T12:00:00+00:00",
        **overrides,
    }
    return ledger.record(**fields)


def test_a_live_fill_is_a_statement_line_with_its_plan_and_bundle(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    _record(ledger)
    lines = ledger.statement_lines(
        start_iso="2026-10-01T00:00:00+00:00", end_iso="2026-11-01T00:00:00+00:00"
    )
    assert len(lines) == 1
    assert lines[0]["owner_id"] == HOST
    assert lines[0]["plan_version"] == 3
    assert lines[0]["bundle_hash"] == "abc123"


def test_a_shadow_fill_never_produces_a_statement_line(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    _record(ledger, live=False)
    assert (
        ledger.statement_lines(
            start_iso="2026-10-01T00:00:00+00:00", end_iso="2026-11-01T00:00:00+00:00"
        )
        == []
    )


def test_a_foreign_owner_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    with pytest.raises(ForeignOwnerError):
        _record(ledger, owner_id="owner-other")
    with sqlite3.connect(tmp_path / "fills.db") as conn:
        assert conn.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 0


def test_statement_window_excludes_fills_outside_the_period(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    _record(ledger, filled_at="2026-09-30T23:59:59+00:00")
    _record(ledger, filled_at="2026-10-15T00:00:00+00:00")
    lines = ledger.statement_lines(
        start_iso="2026-10-01T00:00:00+00:00", end_iso="2026-11-01T00:00:00+00:00"
    )
    assert [line["filled_at"] for line in lines] == ["2026-10-15T00:00:00+00:00"]


PAYLOAD = {"bots": [{"pair": "BTC/USD", "stake_usd": 25}]}


def _header(**overrides: Any) -> dict[str, Any]:
    return {
        "owner_id": HOST,
        "publisher": "owner",
        "kid": "kid-2026-10",
        "plan_version": 1,
        "bundle_hash": bundle_hash(PAYLOAD),
        **overrides,
    }


def test_a_bundle_with_publisher_kid_and_a_matching_hash_is_accepted() -> None:
    header = verify_bundle(_header(), PAYLOAD, host_owner_id=HOST)
    assert (header.publisher, header.kid, header.plan_version) == ("owner", "kid-2026-10", 1)


def test_a_foreign_owner_bundle_is_refused() -> None:
    with pytest.raises(ForeignOwnerError):
        verify_bundle(_header(owner_id="owner-other"), PAYLOAD, host_owner_id=HOST)


def test_an_unaccepted_publisher_or_missing_kid_is_refused() -> None:
    with pytest.raises(ValueError, match="publisher"):
        verify_bundle(_header(publisher="stranger"), PAYLOAD, host_owner_id=HOST)
    with pytest.raises(ValueError, match="kid"):
        verify_bundle(_header(kid=""), PAYLOAD, host_owner_id=HOST)


def test_a_tampered_payload_fails_the_bundle_hash() -> None:
    tampered = {"bots": [{"pair": "BTC/USD", "stake_usd": 2500}]}
    with pytest.raises(ValueError, match="bundle_hash"):
        verify_bundle(_header(), tampered, host_owner_id=HOST)


@pytest.mark.parametrize("bad_version", [0, -1, True, "2"])
def test_plan_version_must_be_a_positive_integer(bad_version: Any) -> None:
    with pytest.raises(ValueError, match="plan_version"):
        verify_bundle(_header(plan_version=bad_version), PAYLOAD, host_owner_id=HOST)


ENROLLED_SUSPENDED = {"enrolled": True}
SUSPENDED = {"suspended": 1}


def test_exits_are_never_gated_even_when_the_license_is_suspended() -> None:
    port = LicenseEntitlements()
    context: dict[str, Any] = {
        "enrollment": ENROLLED_SUSPENDED,
        "status": SUSPENDED,
        "dry_run": False,
    }
    assert port.check("exit", context) == (True, "ok")
    assert port.check("stop", {}) == (True, "ok")


def test_entries_keep_the_license_reason_codes() -> None:
    port = LicenseEntitlements()
    suspended = {"enrollment": ENROLLED_SUSPENDED, "status": SUSPENDED, "dry_run": False}
    assert port.check("enter", suspended) == (False, "license_suspended")
    assert port.check("enter", {"enrollment": {}, "status": {}, "dry_run": False}) == (
        True,
        "free_tier",
    )
    assert port.check("enter", {"enrollment": {}, "status": {}, "dry_run": True}) == (
        True,
        "dry_run",
    )


def test_entries_with_missing_facts_are_refused_not_allowed() -> None:
    port = LicenseEntitlements()
    assert port.check("enter", {}) == (False, "missing_context")
    assert port.check("enter", {"enrollment": {}, "status": {}}) == (False, "missing_context")


def test_an_unknown_action_is_refused() -> None:
    assert LicenseEntitlements().check("withdraw", {}) == (False, "unknown_action")
