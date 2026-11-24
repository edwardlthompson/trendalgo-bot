"""AV-G-BRD6 — LTS header tip count/order matches PySide SCANNER_LTS_HEADER_TIPS."""

from __future__ import annotations

from trendalgo.device import strings as S


def test_lts_header_tips_align_with_titles() -> None:
    assert len(S.SCANNER_LTS_HEADERS) == 17
    assert len(S.SCANNER_LTS_HEADER_TIPS) == len(S.SCANNER_LTS_HEADERS)
    assert S.SCANNER_LTS_HEADERS[0] == "Watch"
    assert "Watchlist" in S.SCANNER_LTS_HEADER_TIPS[0]
    assert S.SCANNER_LTS_HEADERS[3] == "7D%"
    assert "Seven-day percent" in S.SCANNER_LTS_HEADER_TIPS[3]
    assert S.SCANNER_LTS_HEADERS[-1] == "Backtest"
    assert "optimizer" in S.SCANNER_LTS_HEADER_TIPS[-1].lower()
