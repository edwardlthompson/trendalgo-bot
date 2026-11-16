"""Alpaca forex rates → OHLCV points (research/BT only; no FX trading)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any

from trendalgo.brokers.forex_universe import normalize_fx_pair
from trendalgo.market.synthetic import synthetic_ohlcv
from trendalgo.market.types import OhlcvPoint

_DATA_BASE = "https://data.alpaca.markets"
_RATES_PATH = "/v1beta1/forex/rates"


def alpaca_credentials() -> tuple[str, str] | None:
    from trendalgo.device.alpaca_vault import resolve_alpaca_credentials

    return resolve_alpaca_credentials()


def fetch_alpaca_forex_rates(
    pair: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    credentials: tuple[str, str] | None = None,
    opener: Any | None = None,
) -> list[OhlcvPoint]:
    creds = credentials if credentials is not None else alpaca_credentials()
    if creds is None:
        raise RuntimeError("Alpaca credentials missing")
    key, secret = creds
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    fx = normalize_fx_pair(pair)
    # Alpaca uses EURUSD style in some docs; keep slash in currency_pairs.
    tf = "1Day" if timeframe.strip().lower() in {"1d", "1day", "d"} else "1Hour"
    query = urllib.parse.urlencode(
        {
            "currency_pairs": fx,
            "timeframe": tf,
            "start": since.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end": until.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit": "10000",
        }
    )
    url = f"{_DATA_BASE}{_RATES_PATH}?{query}"
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
    with open_fn(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    # Response shape varies; accept rates dict or list.
    rates = payload.get("rates") if isinstance(payload, dict) else None
    rows: list[Any] = []
    if isinstance(rates, dict):
        for _k, vals in rates.items():
            if isinstance(vals, list):
                rows.extend(vals)
    elif isinstance(rates, list):
        rows = rates
    points: list[OhlcvPoint] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ts_raw = str(row.get("t") or row.get("timestamp") or "")
        try:
            when = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        mid = row.get("mid")
        if mid is None:
            bp = row.get("bp")
            ap = row.get("ap")
            if bp is not None and ap is not None:
                mid = (float(bp) + float(ap)) / 2.0
        if mid is None:
            mid = row.get("c") or row.get("close")
        if mid is None:
            continue
        px = float(mid)
        points.append(
            OhlcvPoint(time=int(when.timestamp()), open=px, high=px, low=px, close=px, volume=0.0)
        )
    points.sort(key=lambda p: p.time)
    return points


class AlpacaForexRatesProvider:
    def __init__(self, *, allow_synthetic_fallback: bool = True) -> None:
        self.allow_synthetic_fallback = allow_synthetic_fallback
        self.last_source: str = "none"
        self.last_error: str = ""

    def fetch(
        self,
        exchange_id: str,
        pair: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> list[OhlcvPoint]:
        _ = exchange_id
        fx = normalize_fx_pair(pair)
        if alpaca_credentials() is not None:
            try:
                points = fetch_alpaca_forex_rates(fx, timeframe, since, until)
                if points:
                    self.last_source = "alpaca"
                    return points
            except (
                urllib.error.HTTPError,
                urllib.error.URLError,
                TimeoutError,
                OSError,
                json.JSONDecodeError,
                RuntimeError,
            ) as exc:
                self.last_error = str(exc)
                if not self.allow_synthetic_fallback:
                    raise
        if not self.allow_synthetic_fallback:
            raise RuntimeError("Alpaca forex rates unavailable")
        self.last_source = "synthetic"
        return list(synthetic_ohlcv(fx, timeframe, since, until))
