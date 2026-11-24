"""AV-G-RES2 — Results share tip copy matches PySide."""

from __future__ import annotations

from trendalgo.device import strings as S


def test_results_share_tip() -> None:
    assert "PNG" in S.SCANNER_RESULTS_SHARE_TIP
    assert S.SCANNER_CREATE_BOT == "Create Bot"
