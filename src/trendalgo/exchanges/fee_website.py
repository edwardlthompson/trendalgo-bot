"""Fetch exchange fee schedules from public documentation pages."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, cast

from trendalgo.exchanges.fee_parsers import fees_verified_on_page, parse_fees_from_html

_DEFAULT_TIMEOUT = 25
_USER_AGENT = "TrendAlgo/1.0 (+https://github.com/trendalgo-bot; fee-schedule sync)"


@dataclass(frozen=True)
class FetchedFees:
    taker_pct: float
    maker_pct: float
    source: str
    source_url: str
    verified: bool = False


def fetch_fee_page(url: str, *, timeout: int | None = None) -> str:
    if not url:
        raise ValueError("missing source_url")
    seconds = timeout or int(os.environ.get("TRENDALGO_FEE_FETCH_TIMEOUT", str(_DEFAULT_TIMEOUT)))
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/json,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=seconds) as resp:
        body: str = resp.read(1_500_000).decode("utf-8", errors="ignore")
        return body


def _fee_page_urls(seed: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    primary = str(seed.get("source_url") or "").strip()
    if primary:
        urls.append(primary)
    for alt in seed.get("alternate_urls") or []:
        alt_url = str(alt).strip()
        if alt_url and alt_url not in urls:
            urls.append(alt_url)
    return urls


def _resolve_from_html(
    exchange_id: str,
    html: str,
    *,
    source_url: str,
    seed_taker: float,
    seed_maker: float,
) -> FetchedFees:
    if fees_verified_on_page(html, seed_taker, seed_maker):
        return FetchedFees(
            taker_pct=seed_taker,
            maker_pct=seed_maker,
            source="website_verified",
            source_url=source_url,
            verified=True,
        )

    parsed = parse_fees_from_html(exchange_id, html)
    if parsed is not None and _sane_spot_fees(parsed[0], parsed[1]):
        taker, maker = parsed
        return FetchedFees(
            taker_pct=taker,
            maker_pct=maker,
            source="website",
            source_url=source_url,
            verified=True,
        )

    return FetchedFees(
        taker_pct=seed_taker,
        maker_pct=seed_maker,
        source="documented",
        source_url=source_url,
        verified=False,
    )


def fetch_website_fees(exchange_id: str, seed: dict[str, Any]) -> FetchedFees:
    """Pull fees from the exchange public fee page; fall back to documented seed."""
    seed_taker = float(seed["taker_pct"])
    seed_maker = float(seed["maker_pct"])
    urls = _fee_page_urls(seed)
    if not urls:
        raise ValueError(f"missing source_url for {exchange_id}")

    last_error: Exception | None = None
    best: FetchedFees | None = None

    for url in urls:
        try:
            html = fetch_fee_page(url)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            continue

        result = _resolve_from_html(
            exchange_id,
            html,
            source_url=url,
            seed_taker=seed_taker,
            seed_maker=seed_maker,
        )
        if result.source in ("website_verified", "website"):
            return result
        if best is None or result.source_url == str(seed.get("source_url", "")):
            best = result

    if best is not None:
        return best
    raise RuntimeError(f"website fetch failed: {last_error}") from last_error


def _sane_spot_fees(taker: float, maker: float) -> bool:
    return 0.0001 <= taker <= 0.05 and 0.0 <= maker <= 0.05
