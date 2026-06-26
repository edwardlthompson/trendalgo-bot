"""Boost Mode — premium AI strategy license rate (B1)."""

from __future__ import annotations

from typing import Any

BOOST_LICENSE_RATE = 0.15
STANDARD_LICENSE_RATE = 0.12


def enable_boost_mode(billing_store: Any) -> dict[str, Any]:
    with billing_store._connect() as conn:
        conn.execute(
            """
            UPDATE license_enrollment SET license_rate_pct = ?, updated_at = datetime('now')
            WHERE id = 1
            """,
            (BOOST_LICENSE_RATE,),
        )
    updated = billing_store.get_enrollment()
    return {
        "boost_mode": True,
        "license_rate_pct": BOOST_LICENSE_RATE,
        "enrollment": updated,
        "note": "Higher rate unlocks premium curated AI strategy documentation.",
    }


def disable_boost_mode(billing_store: Any) -> dict[str, Any]:
    with billing_store._connect() as conn:
        conn.execute(
            """
            UPDATE license_enrollment SET license_rate_pct = ?, updated_at = datetime('now')
            WHERE id = 1
            """,
            (STANDARD_LICENSE_RATE,),
        )
    return {
        "boost_mode": False,
        "license_rate_pct": STANDARD_LICENSE_RATE,
        "enrollment": billing_store.get_enrollment(),
    }
