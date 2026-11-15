"""Rolling OHLCVT tip journal append + stitch."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from trendalgo.market.ohlcvt_tip_journal import (
    append_tip,
    journal_span_ready,
    load_journal,
    read_started,
    stitch_with_journal,
)


def _bars(n: int, *, end: datetime | None = None) -> pd.DataFrame:
    end = end or datetime(2026, 12, 15, tzinfo=UTC)
    idx = pd.date_range(end - timedelta(minutes=n - 1), end, freq="1min")
    px = list(range(len(idx)))
    return pd.DataFrame(
        {
            "open": px,
            "high": [v + 1 for v in px],
            "low": [v - 1 for v in px],
            "close": px,
            "volume": [1.0] * len(px),
        },
        index=idx,
    )


def test_append_tip_persists_and_sets_started(tmp_path: Path) -> None:
    tip = _bars(60, end=datetime(2026, 11, 15, 12, tzinfo=UTC))
    out = append_tip(tmp_path, "XBTUSD", tip)
    assert out is not None and len(out) == 60
    loaded = load_journal(tmp_path, "XBTUSD")
    assert loaded is not None and len(loaded) == 60
    assert read_started(tmp_path) == tip.index.min().date()
    assert append_tip(tmp_path, "XBTUSD", None) is not None
    assert append_tip(tmp_path, "", tip) is None


def test_stitch_with_journal_bridges_gap() -> None:
    archive = _bars(10, end=datetime(2026, 9, 30, tzinfo=UTC))
    journal = _bars(10, end=datetime(2026, 11, 15, tzinfo=UTC))
    merged = stitch_with_journal(archive, journal)
    assert len(merged) == 20
    assert merged.index.min() == archive.index.min()
    assert merged.index.max() == journal.index.max()
    assert stitch_with_journal(archive, None).equals(archive)
    empty = archive.iloc[0:0]
    assert stitch_with_journal(empty, journal).equals(journal)


def test_journal_span_ready_requires_30d() -> None:
    short = _bars(60 * 24 * 10)  # 10 days
    assert journal_span_ready(short, today=date_from(short)) is False
    long = _bars(60 * 24 * 31)
    assert journal_span_ready(long, today=date_from(long)) is True
    assert journal_span_ready(None) is False
    assert journal_span_ready(pd.DataFrame()) is False


def date_from(frame: pd.DataFrame):
    end = frame.index.max()
    return end.tz_convert("UTC").date() if end.tzinfo else end.date()
