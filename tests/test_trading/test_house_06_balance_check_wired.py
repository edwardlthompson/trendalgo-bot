"""HOUSE-06: balance_check stays on the pre-trade path (do not delete)."""

from __future__ import annotations

import trendalgo.trading.reconcile as reconcile


def test_reconcile_imports_balance_check() -> None:
    assert callable(reconcile.check_balances)
    assert callable(reconcile.ensure_clear_for_buy)
    assert "balance_check" in reconcile.__doc__ or "balance" in (reconcile.__doc__ or "")
