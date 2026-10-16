"""CM-7: trading code never calls a withdrawal (R-009). Static scan of src/trendalgo/trading."""

from __future__ import annotations

import re
from pathlib import Path

TRADING_DIR = Path(__file__).resolve().parents[2] / "src" / "trendalgo" / "trading"
WITHDRAWAL = re.compile(r"withdraw", re.IGNORECASE)


def test_trading_code_has_no_withdrawal_call() -> None:
    hits: list[str] = []
    for path in sorted(TRADING_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            if WITHDRAWAL.search(line):
                hits.append(f"{path.relative_to(TRADING_DIR)}:{number}")
    assert hits == []
