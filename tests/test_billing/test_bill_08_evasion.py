"""BILL-08: MONETIZATION evasion table maps each vector to a test id."""

from __future__ import annotations

from pathlib import Path

REQUIRED = (
    "test_bill_04_integrity",
    "test_bill_05_monotonic",
    "test_bill_06_identity",
    "test_bill_03_caps",
    "test_grace_timeline",
    "test_monthly_fee",
)


def test_evasion_table_maps_vectors_to_test_ids() -> None:
    text = Path("docs/MONETIZATION.md").read_text(encoding="utf-8")
    assert "## Evasion coverage (BILL-08)" in text
    for needle in REQUIRED:
        assert needle in text, needle
    # eighteen numbered rows
    for n in range(1, 19):
        assert f"| {n} |" in text
