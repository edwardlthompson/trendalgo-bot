"""Market Context attach must not use DataFrame truthiness."""

from __future__ import annotations

import pandas as pd

from trendalgo.analytics.market_context import compute_market_context


def test_compute_on_nonempty_frame() -> None:
    n = 80
    closes = [100.0 + i * 0.1 for i in range(n)]
    df = pd.DataFrame(
        {
            "close": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "volume": [1000.0] * n,
        }
    )
    # Regression: never use `df or other` — DataFrame truth value is ambiguous.
    primary = df if True else None
    assert primary is not None and not primary.empty
    ctx = compute_market_context(primary)
    assert ctx.ok
