"""An OHLC bar as the streaming port sees it. Decisions use closed bars; stops may use a forming one."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Bar:
    timestamp: pd.Timestamp
    high: float
    low: float
    close: float
