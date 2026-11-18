"""Signed monthly license statements (M5, BILL-02/04/07)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

ALPHA_SHARE_FORMULA = "fee = rate * max(0, net - max(bh_net, 0))"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def build_statement(
    period: str,
    rollup: dict[str, float],
    line_items: list[dict[str, Any]],
    *,
    carry_forward_credit_usd: float = 0.0,
    bh_net_usd: float = 0.0,
    excess_usd: float = 0.0,
    benchmark_refs: dict[str, dict[str, Any]] | None = None,
    rate_pct: float | None = None,
    floor_applied: bool = False,
    cap_applied: bool = False,
    share_class: str = "alpha",
) -> dict[str, Any]:
    net_loss = rollup["gross_profit_usd"] <= 0
    note = "Net loss month — license fee $0" if net_loss else ""
    refs = benchmark_refs or {}
    body: dict[str, Any] = {
        "period": period,
        "gross_profit_usd": rollup["gross_profit_usd"],
        "license_fee_usd": rollup["license_fee_usd"],
        "net_benefit_usd": rollup["net_benefit_usd"],
        "bh_net_usd": round(bh_net_usd, 2),
        "excess_usd": round(excess_usd, 2),
        "benchmark_refs": refs,
        "share_class": share_class,
        "rate_pct": rate_pct,
        "floor_applied": floor_applied,
        "cap_applied": cap_applied,
        "carry_forward_credit_usd": carry_forward_credit_usd,
        "net_loss_note": note,
        "line_items": line_items,
        "generated_at": _utc_now(),
        "disclaimer": "Software license calculation only. User initiates payment externally.",
        "formula_footer": ALPHA_SHARE_FORMULA,
    }
    body["signed_hash"] = sign_payload(body)
    return body


def statement_from_stored(row: dict[str, Any]) -> dict[str, Any]:
    """Rebuild a statement view from persisted columns only (no venue re-query)."""
    refs = row.get("benchmark_refs")
    if refs is None and row.get("benchmark_refs_json"):
        refs = json.loads(str(row["benchmark_refs_json"]))
    return {
        "period": row["period"],
        "gross_profit_usd": float(row["gross_profit_usd"]),
        "license_fee_usd": float(row["license_fee_usd"]),
        "net_benefit_usd": float(row.get("net_benefit_usd") or 0),
        "bh_net_usd": float(row.get("bh_net_usd") or 0),
        "excess_usd": float(row.get("excess_usd") or 0),
        "benchmark_refs": refs or {},
        "carry_forward_credit_usd": float(row.get("carry_forward_credit_usd") or 0),
        "net_loss_note": row.get("net_loss_note") or "",
        "signed_hash": row.get("signed_hash"),
        "line_items": row.get("line_items") or [],
        "formula_footer": ALPHA_SHARE_FORMULA,
    }


def sign_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps({k: v for k, v in payload.items() if k != "signed_hash"}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def verify_statement(statement: dict[str, Any]) -> bool:
    expected = sign_payload(statement)
    return hmac_compare(str(statement.get("signed_hash") or ""), expected)


def hmac_compare(left: str, right: str) -> bool:
    if len(left) != len(right):
        return False
    diff = 0
    for a, b in zip(left, right, strict=True):
        diff |= ord(a) ^ ord(b)
    return diff == 0


def export_statement_json(statement: dict[str, Any]) -> str:
    return json.dumps(statement, indent=2)
