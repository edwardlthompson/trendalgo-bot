"""AlgoSpecial free Forex H1 OHLC (research/BT). D1 derived locally from H1."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol

from trendalgo.brokers.forex_universe import normalize_fx_pair
from trendalgo.market.types import OhlcvPoint

_BASE = "https://www.algospecial.com/api/ohlc.php"
_HTTP_TIMEOUT_S = 30
_MAX_RANGE_DAYS = 31
# Free feed often lags wall-clock (empty for "today"); walk back in 30d steps.
_EMPTY_WALK_STEPS = 24
# Reject sparse holiday stubs (e.g. Christmas week) so the walk keeps going.
_MIN_H1_BARS = 120
_LAST_GOOD_UNTIL: datetime | None = None
_429_BACKOFF_S = (5.0, 15.0, 30.0)


class AlgoSpecialUnsupportedError(RuntimeError):
    """HTTP 404 — symbol not listed on the free AlgoSpecial OHLC feed."""


class _Pace(Protocol):
    def wait(self) -> None: ...


def to_algospecial_symbol(pair: str) -> str:
    fx = normalize_fx_pair(pair)
    return fx.replace("/", "")


def fetch_algospecial_h1(
    pair: str,
    since: datetime,
    until: datetime,
    *,
    opener: Any | None = None,
    pace: _Pace | None = None,
) -> list[OhlcvPoint]:
    """Fetch up to 31d of H1 bars. Walks back when the free feed has no rows for wall-clock dates.

    Raises ``AlgoSpecialUnsupportedError`` on HTTP 404 (no walk-back / retries).
    """
    global _LAST_GOOD_UNTIL
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    span = min(_MAX_RANGE_DAYS, max(1, (until - since).days))
    ends: list[datetime] = [until]
    if _LAST_GOOD_UNTIL is not None and _LAST_GOOD_UNTIL < until:
        ends.insert(0, _LAST_GOOD_UNTIL)
    seen: set[str] = set()
    best: list[OhlcvPoint] = []

    def _consider(points: list[OhlcvPoint]) -> list[OhlcvPoint] | None:
        nonlocal best
        if not points:
            return None
        if len(points) > len(best):
            best = points
        if len(points) >= _MIN_H1_BARS:
            _LAST_GOOD_UNTIL = datetime.fromtimestamp(points[-1].time, tz=UTC)
            return points
        return None

    for end in ends:
        key = end.astimezone(UTC).strftime("%Y-%m-%d")
        if key in seen:
            continue
        seen.add(key)
        hit = _consider(
            _request_h1_window(pair, end - timedelta(days=span), end, opener=opener, pace=pace)
        )
        if hit is not None:
            return hit
    # Empty/sparse primary window — walk calendar back (provider lag / holidays).
    cursor = until
    for _ in range(_EMPTY_WALK_STEPS):
        cursor = cursor - timedelta(days=30)
        key = cursor.astimezone(UTC).strftime("%Y-%m-%d")
        if key in seen:
            continue
        seen.add(key)
        hit = _consider(
            _request_h1_window(
                pair, cursor - timedelta(days=span), cursor, opener=opener, pace=pace
            )
        )
        if hit is not None:
            return hit
    if best:
        _LAST_GOOD_UNTIL = datetime.fromtimestamp(best[-1].time, tz=UTC)
    return best


def _request_h1_window(
    pair: str,
    since: datetime,
    until: datetime,
    *,
    opener: Any | None,
    pace: _Pace | None = None,
) -> list[OhlcvPoint]:
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
    last_exc: BaseException | None = None
    for attempt, delay in enumerate((0.0, *_429_BACKOFF_S)):
        if delay > 0:
            time.sleep(delay)
        if pace is not None:
            pace.wait()
        try:
            with open_fn(req, timeout=_HTTP_TIMEOUT_S) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise AlgoSpecialUnsupportedError(
                    f"{normalize_fx_pair(pair)} not on AlgoSpecial"
                ) from exc
            if exc.code == 429 and attempt < len(_429_BACKOFF_S):
                last_exc = exc
                continue
            raise
    else:
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("AlgoSpecial request failed")
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
