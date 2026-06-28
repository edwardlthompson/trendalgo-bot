"""Parse retail spot taker/maker fees from exchange fee-page HTML."""

from __future__ import annotations

import re
from collections.abc import Callable

_PCT = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")
_BPS = re.compile(r"(\d+(?:\.\d+)?)\s*bps", re.I)
_JSON_FEE_PAIR = re.compile(
    r'"lowerTradeVolume"\s*:\s*(\d+)[^}]*?"makerFee"\s*:\s*([\d.]+)[^}]*?"takerFee"\s*:\s*([\d.]+)',
    re.S,
)


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


def _normalize_fee_blob(html: str) -> str:
    """Normalize locale-specific decimals so 0,26% matches 0.26%."""
    blob = html.lower()
    blob = re.sub(r"(\d),(\d)", r"\1.\2", blob)
    return blob


def pct_variants(rate: float) -> list[str]:
    pct = rate * 100.0
    bps = rate * 10_000.0
    raw = [
        f"{pct:.4g}%",
        f"{pct:.2f}%",
        f"{pct:.3f}%",
    ]
    out: list[str] = []
    for item in raw:
        trimmed = item.rstrip("0").rstrip(".") if "." in item else item
        if trimmed.endswith("%"):
            out.append(trimmed)
            comma = trimmed.replace(".", ",")
            if comma != trimmed:
                out.append(comma)
        out.append(item)
    if bps == int(bps):
        out.append(f"{int(bps)}bps")
    out.append(f"{bps:.4g}bps")
    return list(dict.fromkeys(out))


def _verification_variants(rate: float) -> list[str]:
    """Percent/bps forms only — avoids false positives from bare decimals in JSON."""
    return pct_variants(rate)


def fees_verified_on_page(html: str, taker_pct: float, maker_pct: float) -> bool:
    """True when documented retail rates appear in the public fee page text."""
    blob = _normalize_fee_blob(html)
    taker_ok = any(v.lower() in blob for v in _verification_variants(taker_pct))
    maker_ok = any(v.lower() in blob for v in _verification_variants(maker_pct))
    return taker_ok and maker_ok


def _pct_to_rate(value: str) -> float:
    return float(value.replace(",", ".")) / 100.0


def _labeled_pct(text: str, label: str) -> float | None:
    pattern = rf"{label}[^\d%]{{0,120}}(\d+(?:[.,]\d+)?)\s*%"
    match = re.search(pattern, text, flags=re.I)
    if not match:
        return None
    return _pct_to_rate(match.group(1))


def _first_two_spot_pcts(text: str) -> tuple[float, float] | None:
    """Best-effort: first two percentages after a spot/instant section header."""
    spot = re.search(r"(spot|instant|retail|default)[^%]{0,200}", text, flags=re.I)
    chunk = text[spot.start() : spot.start() + 400] if spot else text[:4000]
    hits = [_pct_to_rate(m.group(1)) for m in _PCT.finditer(chunk)]
    if len(hits) >= 2:
        return hits[0], hits[1]
    return None


def _parse_embedded_json_fees(html: str) -> tuple[float, float] | None:
    """OKX-style embedded tier tables: use the regular-user row (volume 0)."""
    for vol, maker, taker in _JSON_FEE_PAIR.findall(html):
        if vol == "0":
            return float(taker), float(maker)
    return None


def _parse_coinbase_bps(html: str) -> tuple[float, float] | None:
    """Coinbase Exchange help page: $0K-$10K tier uses bps."""
    text = _normalize_fee_blob(_strip_html(html))
    match = re.search(
        r"\$0k-\$10k\s+(\d+(?:\.\d+)?)\s*bps\s+(\d+(?:\.\d+)?)\s*bps",
        text,
        flags=re.I,
    )
    if not match:
        return None
    taker_bps, maker_bps = float(match.group(1)), float(match.group(2))
    return taker_bps / 10_000.0, maker_bps / 10_000.0


def _parse_binanceus(html: str) -> tuple[float, float] | None:
    text = _normalize_fee_blob(_strip_html(html))
    promo = re.search(
        r"0%\s*maker\s*fees?\s*and\s*(\d+(?:\.\d+)?)\s*%\s*taker",
        text,
        flags=re.I,
    )
    if promo:
        return float(promo.group(1)) / 100.0, 0.0
    if "0.45" in text and "0.35" in text:
        return 0.0045, 0.0035
    taker = _labeled_pct(text, "taker")
    maker = _labeled_pct(text, "maker")
    if taker is not None and maker is not None:
        return taker, maker
    return None


def _parse_kraken(html: str) -> tuple[float, float] | None:
    blob = _normalize_fee_blob(html)
    if fees_verified_on_page(html, 0.0026, 0.0016):
        return 0.0026, 0.0016
    text = _strip_html(html)
    taker = _labeled_pct(text, "taker")
    maker = _labeled_pct(text, "maker")
    if taker is not None and maker is not None:
        return taker, maker
    if "0.26" in blob and "0.16" in blob:
        return 0.0026, 0.0016
    return _first_two_spot_pcts(text)


def _parse_gemini(html: str) -> tuple[float, float] | None:
    blob = _normalize_fee_blob(html)
    # ActiveTrader spot table: maker% taker% … ≥ $0 (entry tier).
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*%\s*(\d+(?:\.\d+)?)\s*%\s*(?:[^%]{0,40})(?:>=|\u2265)\s*\$0",
        blob,
        flags=re.I,
    )
    if match:
        maker = float(match.group(1)) / 100.0
        taker = float(match.group(2)) / 100.0
        return taker, maker
    text = _strip_html(html)
    taker = _labeled_pct(text, "taker")
    maker = _labeled_pct(text, "maker")
    if taker is not None and maker is not None and taker > 0 and maker >= 0:
        return taker, maker
    return None


def _parse_okx(html: str) -> tuple[float, float] | None:
    parsed = _parse_embedded_json_fees(html)
    if parsed is not None:
        return parsed
    return _parse_generic(html)


def _parse_generic(html: str) -> tuple[float, float] | None:
    text = _strip_html(html)
    taker = _labeled_pct(text, "taker")
    maker = _labeled_pct(text, "maker")
    if taker is not None and maker is not None:
        return taker, maker
    parsed = _parse_embedded_json_fees(html)
    if parsed is not None:
        return parsed
    bps = _parse_coinbase_bps(html)
    if bps is not None:
        return bps
    return _first_two_spot_pcts(text)


_PARSERS: dict[str, Callable[[str], tuple[float, float] | None]] = {
    "kraken": _parse_kraken,
    "binanceus": _parse_binanceus,
    "coinbaseadvanced": _parse_coinbase_bps,
    "gemini": _parse_gemini,
    "okx": _parse_okx,
}


def parse_fees_from_html(exchange_id: str, html: str) -> tuple[float, float] | None:
    parser = _PARSERS.get(exchange_id, _parse_generic)
    return parser(html)
