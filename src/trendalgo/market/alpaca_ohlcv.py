"""Alpaca equity OHLCV provider — HTTP when keyed; synthetic offline (no SDK on CI)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from trendalgo.market.synthetic import synthetic_ohlcv
from trendalgo.market.types import OhlcvPoint

# done_chunks (1-based), total_chunks, sample_symbol
ChunkProgress = Callable[[int, int, str], None]

_DATA_BASE = "https://data.alpaca.markets"
_BARS_PATH = "/v2/stocks/{symbol}/bars"
_MULTI_BARS_PATH = "/v2/stocks/bars"
_HTTP_TIMEOUT_S = 15
# Free/Basic plan ≈ 200 calls/min — stay under with headroom.
_FREE_PLAN_MAX_CALLS_PER_MIN = 180
_DEFAULT_MULTI_CHUNK = 100


def normalize_alpaca_symbol(pair: str) -> str:
    raw = pair.strip().upper().replace(" ", "")
    if "/" in raw:
        raw = raw.split("/", 1)[0]
    return raw


def alpaca_credentials() -> tuple[str, str] | None:
    from trendalgo.device.alpaca_vault import resolve_alpaca_credentials

    return resolve_alpaca_credentials()


def _timeframe_param(timeframe: str) -> str:
    tf = timeframe.strip().lower()
    mapping = {"1d": "1Day", "1h": "1Hour", "1m": "1Min", "5m": "5Min", "15m": "15Min"}
    return mapping.get(tf, "1Day")


def fetch_alpaca_equity_bars(
    symbol: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    credentials: tuple[str, str] | None = None,
    opener: Any | None = None,
) -> list[OhlcvPoint]:
    """Fetch bars from Alpaca Market Data API. Raises on HTTP/parse failure."""
    creds = credentials if credentials is not None else alpaca_credentials()
    if creds is None:
        raise RuntimeError("Alpaca credentials missing")
    key, secret = creds
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    sym = normalize_alpaca_symbol(symbol)
    query = urllib.parse.urlencode(
        {
            "timeframe": _timeframe_param(timeframe),
            "start": since.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": until.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": "10000",
            "adjustment": "raw",
            "feed": "iex",
        }
    )
    url = f"{_DATA_BASE}{_BARS_PATH.format(symbol=urllib.parse.quote(sym))}?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
        },
        method="GET",
    )
    open_fn = opener or urllib.request.urlopen
    with open_fn(req, timeout=_HTTP_TIMEOUT_S) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    bars = payload.get("bars") or []
    return _parse_bar_rows(bars if isinstance(bars, list) else [])


def _parse_bar_rows(bars: list[Any]) -> list[OhlcvPoint]:
    points: list[OhlcvPoint] = []
    for row in bars:
        if not isinstance(row, dict):
            continue
        ts_raw = str(row.get("t") or "")
        try:
            when = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        points.append(
            OhlcvPoint(
                time=int(when.timestamp()),
                open=float(row.get("o") or 0),
                high=float(row.get("h") or 0),
                low=float(row.get("l") or 0),
                close=float(row.get("c") or 0),
                volume=float(row.get("v") or 0),
            )
        )
    return points


def fetch_alpaca_equity_bars_multi(
    symbols: list[str],
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    credentials: tuple[str, str] | None = None,
    opener: Any | None = None,
    chunk_size: int = _DEFAULT_MULTI_CHUNK,
    max_calls_per_min: float = _FREE_PLAN_MAX_CALLS_PER_MIN,
    on_chunk: ChunkProgress | None = None,
) -> dict[str, list[OhlcvPoint]]:
    """Multi-symbol bars via GET /v2/stocks/bars (paginated, free-plan paced)."""
    creds = credentials if credentials is not None else alpaca_credentials()
    if creds is None:
        raise RuntimeError("Alpaca credentials missing")
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    key, secret = creds
    open_fn = opener or urllib.request.urlopen
    out: dict[str, list[OhlcvPoint]] = {}
    cleaned = [normalize_alpaca_symbol(s) for s in symbols if str(s).strip()]
    min_interval = 60.0 / max(1.0, float(max_calls_per_min))
    last_call = 0.0
    size = max(1, int(chunk_size))
    total_chunks = max(1, (len(cleaned) + size - 1) // size) if cleaned else 0
    for i in range(0, len(cleaned), size):
        chunk = cleaned[i : i + size]
        page_token: str | None = None
        while True:
            elapsed = time.monotonic() - last_call
            if last_call > 0 and elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            params: dict[str, str] = {
                "symbols": ",".join(chunk),
                "timeframe": _timeframe_param(timeframe),
                "start": since.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end": until.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "limit": "10000",
                "adjustment": "raw",
                "feed": "iex",
            }
            if page_token:
                params["page_token"] = page_token
            url = f"{_DATA_BASE}{_MULTI_BARS_PATH}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(
                url,
                headers={
                    "APCA-API-KEY-ID": key,
                    "APCA-API-SECRET-KEY": secret,
                    "Accept": "application/json",
                },
                method="GET",
            )
            with open_fn(req, timeout=_HTTP_TIMEOUT_S) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            last_call = time.monotonic()
            bars_map = payload.get("bars") if isinstance(payload, dict) else None
            if isinstance(bars_map, dict):
                for sym, rows in bars_map.items():
                    if not isinstance(rows, list):
                        continue
                    points = _parse_bar_rows(rows)
                    if not points:
                        continue
                    key_sym = str(sym).upper()
                    out.setdefault(key_sym, []).extend(points)
            token = payload.get("next_page_token") if isinstance(payload, dict) else None
            page_token = str(token) if token else None
            if not page_token:
                break
        for sym, points in list(out.items()):
            points.sort(key=lambda p: p.time)
            out[sym] = points
        if on_chunk is not None and chunk:
            done = (i // size) + 1
            on_chunk(done, total_chunks, chunk[0])
    return out


class AlpacaOhlcvProvider:
    """OhlcvProvider-compatible equity bars; synthetic when unkeyed or fetch fails."""

    def __init__(self, *, allow_synthetic_fallback: bool = True) -> None:
        self.allow_synthetic_fallback = allow_synthetic_fallback
        self.last_source: str = "none"

    def fetch(
        self,
        exchange_id: str,
        pair: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> list[OhlcvPoint]:
        _ = exchange_id
        sym = normalize_alpaca_symbol(pair)
        if alpaca_credentials() is not None:
            try:
                points = fetch_alpaca_equity_bars(sym, timeframe, since, until)
                if points:
                    self.last_source = "alpaca"
                    return points
            except (
                urllib.error.URLError,
                TimeoutError,
                OSError,
                json.JSONDecodeError,
                RuntimeError,
            ):
                if not self.allow_synthetic_fallback:
                    raise
        if not self.allow_synthetic_fallback:
            raise RuntimeError("Alpaca bars unavailable")
        self.last_source = "synthetic"
        return list(synthetic_ohlcv(f"{sym}/USD", timeframe, since, until))
