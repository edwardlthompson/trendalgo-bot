"""AlgoSpecial free Forex H1 OHLC (research/BT). D1 derived locally from H1."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta
from typing import Any

from trendalgo.brokers.forex_universe import normalize_fx_pair
from trendalgo.market.types import OhlcvPoint

_BASE = "https://www.algospecial.com/api/ohlc.php"
_HTTP_TIMEOUT_S = 30
_MAX_RANGE_DAYS = 31


def to_algospecial_symbol(pair: str) -> str:
    fx = normalize_fx_pair(pair)
    return fx.replace("/", "")


def fetch_algospecial_h1(
    pair: str,
    since: datetime,
    until: datetime,
    *,
    opener: Any | None = None,
) -> list[OhlcvPoint]:
    """Fetch up to 31d of H1 bars for one FX pair. Raises on HTTP/parse failure."""
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    # Clamp to API max window (keep the most recent end).
    if (until - since).days > _MAX_RANGE_DAYS:
        since = until - timedelta(days=_MAX_RANGE_DAYS)
    symbol = to_algospecial_symbol(pair)
    query = urllib.parse.urlencode(
        {
            "symbol": symbol,
            "tf": "H1",
            "from": since.astimezone(UTC).strftime("%Y-%m-%d"),
            "to": until.astimezone(UTC).strftime("%Y-%m-%d"),
            "format": "json",
        }
    )
    url = f"{_BASE}?{query}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    open_fn = opener or urllib.request.urlopen
    with open_fn(req, timeout=_HTTP_TIMEOUT_S) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    rows = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    return parse_algospecial_rows(rows)


def parse_algospecial_rows(rows: list[Any]) -> list[OhlcvPoint]:
    """Parse AlgoSpecial OHLC row dicts → OhlcvPoint (oldest→newest)."""
    points: list[OhlcvPoint] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ts = _parse_timestamp(row.get("Timestamp") or row.get("timestamp"))
        if ts is None:
            continue
        try:
            o = _num(row.get("Open"), row.get("o"))
            h = _num(row.get("High"), row.get("h"))
            low = _num(row.get("Low"), row.get("l"))
            c = _num(row.get("Close"), row.get("c"))
            vol = _num(row.get("TickVolume"), row.get("volume"), default=0.0)
            points.append(
                OhlcvPoint(
                    time=int(ts.timestamp()),
                    open=o,
                    high=h,
                    low=low,
                    close=c,
                    volume=vol,
                )
            )
        except (TypeError, ValueError):
            continue
    points.sort(key=lambda p: p.time)
    return points


def _num(*candidates: object, default: float | None = None) -> float:
    for raw in candidates:
        if isinstance(raw, bool):
            continue
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str) and raw.strip():
            return float(raw)
    if default is not None:
        return float(default)
    raise ValueError("missing numeric field")


def derive_daily_from_h1(hourly: list[OhlcvPoint]) -> list[OhlcvPoint]:
    """Aggregate H1 bars into UTC calendar-day OHLCV (volume summed)."""
    by_day: dict[date, list[OhlcvPoint]] = {}
    for bar in hourly:
        day = datetime.fromtimestamp(bar.time, tz=UTC).date()
        by_day.setdefault(day, []).append(bar)
    out: list[OhlcvPoint] = []
    for day in sorted(by_day):
        bars = by_day[day]
        if not bars:
            continue
        out.append(
            OhlcvPoint(
                time=int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp()),
                open=float(bars[0].open),
                high=max(float(b.high) for b in bars),
                low=min(float(b.low) for b in bars),
                close=float(bars[-1].close),
                volume=sum(float(b.volume) for b in bars),
            )
        )
    return out


def _parse_timestamp(raw: object) -> datetime | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    # AlgoSpecial: "2025.10.01 01:00:00"
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None
