"""BILL-07: two-class pricing formula + examples in docs/strings/statements."""

from __future__ import annotations

from pathlib import Path

from trendalgo.billing.statements import ALPHA_SHARE_FORMULA, build_statement
from trendalgo.device import strings as S


def test_formula_verbatim_on_statement_footer_and_strings() -> None:
    assert S.BILLING_ALPHA_FORMULA == ALPHA_SHARE_FORMULA
    assert ALPHA_SHARE_FORMULA in S.BILLING_ALPHA_BODY
    stmt = build_statement(
        "2026-06",
        {"gross_profit_usd": 200.0, "license_fee_usd": 6.0, "net_benefit_usd": 194.0},
        [],
        bh_net_usd=80.0,
        excess_usd=120.0,
    )
    assert stmt["formula_footer"] == ALPHA_SHARE_FORMULA


def test_three_worked_examples_present() -> None:
    examples = S.BILLING_PRICING_EXAMPLES
    assert "bull-beat" in examples and "$6.00" in examples
    assert "bull-trail" in examples and "$0" in examples
    assert "bear" in examples


def test_monetization_doc_has_formula() -> None:
    text = Path("docs/MONETIZATION.md").read_text(encoding="utf-8")
    assert ALPHA_SHARE_FORMULA in text
    assert "Alpha Share" in text and "Standard Share" in text
