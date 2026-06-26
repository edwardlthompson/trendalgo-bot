"""Signed monthly license statements (M5)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_statement(
    period: str,
    rollup: dict[str, float],
    line_items: list[dict[str, Any]],
    *,
    carry_forward_credit_usd: float = 0.0,
) -> dict[str, Any]:
    net_loss = rollup["gross_profit_usd"] <= 0
    note = "Net loss month — license fee $0" if net_loss else ""
    body = {
        "period": period,
        "gross_profit_usd": rollup["gross_profit_usd"],
        "license_fee_usd": rollup["license_fee_usd"],
        "net_benefit_usd": rollup["net_benefit_usd"],
        "carry_forward_credit_usd": carry_forward_credit_usd,
        "net_loss_note": note,
        "line_items": line_items,
        "generated_at": _utc_now(),
        "disclaimer": "Software license calculation only. User initiates payment externally.",
    }
    body["signed_hash"] = sign_payload(body)
    return body


def sign_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps({k: v for k, v in payload.items() if k != "signed_hash"}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def export_statement_json(statement: dict[str, Any]) -> str:
    return json.dumps(statement, indent=2)
