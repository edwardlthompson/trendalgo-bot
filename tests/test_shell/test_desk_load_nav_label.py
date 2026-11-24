"""AV-G-STR1 — desk-load nav label format matches BOARD_LOAD_TAB."""

from __future__ import annotations

from trendalgo.device import strings as S


def test_board_load_tab_format() -> None:
    assert S.BOARD_LOAD_TAB.format(label="Crypto", pct=42) == "Crypto · 42%"
    assert S.BOARD_LOAD_TAB.format(label="TradFi", pct=0) == "TradFi · 0%"
    assert S.BOARD_LOAD_TAB.format(label="Forex", pct=100) == "Forex · 100%"


def test_running_frac_to_percent() -> None:
    """Mirror Avalonia ParseDeskLoadPercent(running:done/total)."""

    def parse(job: str) -> int | None:
        if not job.startswith("running:") or "/" not in job:
            return None
        frac = job.removeprefix("running:")
        done_s, total_s = frac.split("/", 1)
        done, total = int(done_s), int(total_s)
        if total <= 0:
            return None
        return max(0, min(100, 100 * done // total))

    assert parse("running:3/10") == 30
    assert parse("running:10/10") == 100
    assert parse("idle") is None
