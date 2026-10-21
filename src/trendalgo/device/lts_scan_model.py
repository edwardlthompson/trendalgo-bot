"""LTS table rows for the device Scanner: build, save, load, normalize. Pure; no Qt."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json
from trendalgo.device.scan_identity import (
    coin_exchange_id,
    row_key,
    stamp_exchange,
)
from trendalgo.scanner.snapshot import OpportunityRow, QualifiedSnapshot

LTS_ROWS_FILE = "lts_scan_rows.json"
WATCHLIST_FILE = "scanner_watchlist.json"
FILTERS_FILE = "scanner_filters.json"
# Legacy single-select labels (tests / old filters). Prefer scan_exchanges ids.
EXCHANGES = ("All", "Kraken", "Coinbase")


def lts_rows_path(root: Path) -> Path:
    return root / LTS_ROWS_FILE


def save_lts_rows(root: Path, rows: list[dict[str, Any]]) -> None:
    prior = {row_key(r) for r in load_lts_rows(root)}
    write_json(
        lts_rows_path(root),
        {"rows": [normalize_coin(r, prior_keys=prior) for r in rows]},
    )


def load_lts_rows(root: Path) -> list[dict[str, Any]]:
    data = read_json(lts_rows_path(root))
    if data is None:
        return []
    rows = data.get("rows")
    if not isinstance(rows, list):
        return []
    return [normalize_coin(r) for r in rows if isinstance(r, dict)]


def build_lts_rows(
    snapshot: QualifiedSnapshot,
    *,
    enrich_charts: bool,
    exchange_id: str = "kraken",
) -> list[dict[str, Any]]:
    """Map a snapshot to LTS coin dicts stamped with one venue."""
    eid = exchange_id.strip().lower() or "kraken"
    if enrich_charts:
        from trendalgo.lts_vendor.bridge import opportunities_to_final_results

        raw = opportunities_to_final_results(snapshot)
    else:
        raw = [_basic_row(row) for row in snapshot.opportunities]
    return [normalize_coin(stamp_exchange(r, eid)) for r in raw]


def _basic_row(row: OpportunityRow) -> dict[str, Any]:
    from trendalgo.device.coin_health import compute_coin_health

    symbol = row.pair.split("/")[0].strip().upper() or row.pair.upper()
    gain = float(row.gain_pct) * 100.0
    out = {
        "symbol": symbol,
        "name": symbol,
        "pair": row.pair,
        "exchange_id": "kraken",
        "gains": {"7d": gain, "30d": gain},
        "uniformity_score": float(row.uniformity) * 100.0,
        "volume_24h": float(row.volume_score),
        "listed_on": ["kraken"],
        "chart_closes_1h": list(row.sparkline),
        "chart_closes_1d": [],
        "bot_vs_bh_pct": None,
        "bot_best_net_pct": None,
        "volume_acceleration_pct": None,
        "max_drawdown_pct": None,
        "hv_7d_pct": None,
    }
    out["health_score"] = compute_coin_health(out)
    return out


def closes_pct_from_high(closes: list[float]) -> float | None:
    """Percent the last close sits below the window high (closesPctFromHigh)."""
    if len(closes) < 2:
        return None
    high = max(closes)
    last = closes[-1]
    if high <= 0:
        return None
    return ((high - last) / high) * 100.0


def normalize_coin(
    coin: dict[str, Any],
    *,
    prior_symbols: set[str] | None = None,
    prior_keys: set[str] | None = None,
) -> dict[str, Any]:
    """Flatten risk_context, dual chart keys, chart-dist %, and optional NEW badge."""
    out = dict(coin)
    eid = coin_exchange_id(out)
    out["exchange_id"] = eid
    out["listed_on"] = [eid]
    closes_1h = cell_closes(out, "closes_1h")
    risk = out.get("risk_context")
    if not isinstance(risk, dict) and len(closes_1h) >= 8:
        from trendalgo.lts_vendor.utils.scan_artifacts import risk_context_from_hourly_closes

        risk = risk_context_from_hourly_closes(closes_1h)
        if risk:
            out["risk_context"] = risk
    if isinstance(risk, dict):
        if out.get("hv_7d_pct") is None and risk.get("hv_7d_annualized_pct") is not None:
            out["hv_7d_pct"] = risk.get("hv_7d_annualized_pct")
        if out.get("max_drawdown_pct") is None and risk.get("max_drawdown_30d_pct") is not None:
            out["max_drawdown_pct"] = risk.get("max_drawdown_30d_pct")
    # Both windows from hourly closes (local enrich); matches spark series in the table.
    window_7d = closes_1h[-168:] if closes_1h else []
    window_30d = closes_1h[-720:] if closes_1h else []
    out["spark_closes_7d"] = list(window_7d)
    out["spark_closes_30d"] = list(window_30d)
    out["chart_dist_7d_pct"] = closes_pct_from_high(window_7d)
    out["chart_dist_30d_pct"] = closes_pct_from_high(window_30d)
    from trendalgo.device.coin_health import compute_coin_health

    out["health_score"] = compute_coin_health(out)
    keys = prior_keys
    if keys is None and prior_symbols is not None:
        # Legacy callers passed bare symbols.
        keys = set(prior_symbols)
    if keys is not None:
        key = row_key(out)
        out["is_new"] = bool(key) and key not in keys and bool(keys)
    return out


def load_watchlist(root: Path) -> list[str]:
    data = read_json(root / WATCHLIST_FILE)
    if data is None:
        return []
    pairs = data.get("pairs")
    return [str(p) for p in pairs] if isinstance(pairs, list) else []


def save_watchlist(root: Path, pairs: list[str]) -> None:
    write_json(root / WATCHLIST_FILE, {"pairs": pairs})


def load_filters(root: Path) -> dict[str, Any]:
    data = read_json(root / FILTERS_FILE)
    return dict(data) if isinstance(data, dict) else {}


def save_filters(root: Path, filters: dict[str, Any]) -> None:
    write_json(root / FILTERS_FILE, filters)


def coins_for_backtest(
    coins: list[dict[str, Any]], filters: dict[str, Any]
) -> list[dict[str, Any]]:
    """Pass-1 BT queue: every Qualified coin that still clears the scan volume floor.

    Column 7d/30d / chart-dist / health filters only narrow the *table* view
    (`scanner_page`). Re-applying them here left Qualified rows with empty
    Results after a volume-first scan.
    """
    return filter_coins(
        coins,
        vol24_min=_positive_floor(
            filters.get("vol24_min")
            if filters.get("vol24_min") not in (None, "")
            else filters.get("min_volume_usd")
        ),
    )


def _positive_floor(raw: object) -> float | None:
    value = _opt_filter_float(raw)
    return value if value is not None and value > 0 else None


def _opt_filter_float(raw: object) -> float | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def filter_coins(
    coins: list[dict[str, Any]],
    *,
    exchange: str = "All",
    exchanges: list[str] | None = None,
    min_gain_7d: float | None = None,
    min_gain_30d: float | None = None,
    min_best_bt: float | None = None,
    bot_vs_bh_filter: str | None = None,
    chart_dist_max_7d: float | None = None,
    chart_dist_max_30d: float | None = None,
    health_min: float | None = None,
    uniformity_min: float | None = None,
    vol_accel_filter: str | None = None,
    vol24_min: float | None = None,
) -> list[dict[str, Any]]:
    """Client-side display filters. Scan gate stays in scan_model."""
    from trendalgo.device.portfolio_categories import is_stablecoin_base

    allowed = _exchange_allow_set(exchange=exchange, exchanges=exchanges)
    out: list[dict[str, Any]] = []
    for coin in coins:
        pair = str(coin.get("pair") or coin.get("symbol") or "")
        if is_stablecoin_base(pair):
            continue
        eid = coin_exchange_id(coin)
        if allowed is not None and eid not in allowed:
            continue
        g7 = cell_gain(coin, "7d")
        g30 = cell_gain(coin, "30d")
        if not _pass_min_floor(g7, min_gain_7d):
            continue
        if not _pass_min_floor(g30, min_gain_30d):
            continue
        if not _pass_min_floor(_as_float(coin.get("bot_best_net_pct")), min_best_bt):
            continue
        if not _pass_bot_vs_bh(coin.get("bot_vs_bh_pct"), bot_vs_bh_filter):
            continue
        if not _pass_chart_dist(coin.get("chart_dist_7d_pct"), chart_dist_max_7d):
            continue
        if not _pass_chart_dist(coin.get("chart_dist_30d_pct"), chart_dist_max_30d):
            continue
        if health_min is not None:
            score = _as_float(coin.get("health_score"))
            if score is None or score < health_min:
                continue
        if uniformity_min is not None:
            score = _as_float(coin.get("uniformity_score"))
            if score is None or score < uniformity_min:
                continue
        if not _pass_vol_accel(coin.get("volume_acceleration_pct"), vol_accel_filter):
            continue
        if vol24_min is not None:
            vol = _as_float(coin.get("volume_24h"))
            if vol is None or vol < vol24_min:
                continue
        out.append(coin)
    return out


def _exchange_allow_set(*, exchange: str, exchanges: list[str] | None) -> set[str] | None:
    """None = allow all venues; empty set = allow none; else allow listed ids."""
    if exchanges is not None:
        cleaned = {str(x).strip().lower() for x in exchanges if str(x).strip()}
        # Empty checklist means "show none" only when explicitly provided as [].
        return cleaned
    venue = exchange.strip().lower()
    if venue in ("", "all"):
        return None
    # Legacy brand labels → registry-ish ids.
    aliases = {
        "kraken": "kraken",
        "coinbase": "coinbaseadvanced",
        "coinbaseadvanced": "coinbaseadvanced",
        "binance.us": "binanceus",
        "binanceus": "binanceus",
    }
    return {aliases.get(venue, venue)}


def _pass_min_floor(value: float | None, floor: float | None) -> bool:
    """None floor = off; 0 = strictly positive; N>0 = value >= N."""
    if floor is None:
        return True
    if value is None:
        return False
    if floor == 0:
        return value > 0
    return value >= floor


def _pass_bot_vs_bh(raw: object, filt: str | None) -> bool:
    """pos = bot beat B&H; neg = B&H beat the bot (buy-and-hold edge)."""
    if not filt:
        return True
    value = _as_float(raw)
    if value is None:
        return False
    if filt == "pos":
        return value > 0
    if filt == "neg":
        return value < 0
    return True


def _as_float(raw: object) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int | float | str):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
    return None


def _pass_chart_dist(raw: object, max_pct: float | None) -> bool:
    """Exclude when % below high is at or above the threshold (Ex ≥N%)."""
    if max_pct is None:
        return True
    value = _as_float(raw)
    if value is None:
        return True
    return value < max_pct


def _pass_vol_accel(raw: object, filt: str | None) -> bool:
    if not filt:
        return True
    value = _as_float(raw)
    if value is None:
        return False
    if filt == "pos":
        return value > 0
    threshold = _as_float(filt)
    return True if threshold is None else value >= threshold


def cell_gain(coin: dict[str, Any], key: str) -> float | None:
    gains = coin.get("gains")
    if not isinstance(gains, dict):
        return None
    raw = gains.get(key)
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def cell_closes(coin: dict[str, Any], key: str) -> list[float]:
    """Prefer closes_1h/closes_1d; fall back to chart_closes_* for basic rows."""
    aliases = {
        "closes_1h": ("closes_1h", "chart_closes_1h"),
        "closes_1d": ("closes_1d", "chart_closes_1d"),
        "chart_closes_1h": ("chart_closes_1h", "closes_1h"),
        "chart_closes_1d": ("chart_closes_1d", "closes_1d"),
    }
    for name in aliases.get(key, (key,)):
        raw = coin.get(name)
        if not isinstance(raw, list) or not raw:
            continue
        out: list[float] = []
        for value in raw:
            try:
                out.append(float(value))
            except (TypeError, ValueError):
                continue
        if out:
            return out
    return []


def has_backtest_results(coin: dict[str, Any]) -> bool:
    if coin.get("bot_best_net_pct") is not None:
        return True
    tops = coin.get("backtest_top_strategies")
    return isinstance(tops, list) and bool(tops)


def dash(value: object, *, pct: bool = False, money: bool = False) -> str:
    if value is None:
        return "—"
    try:
        if isinstance(value, bool):
            return "—"
        if isinstance(value, int | float):
            number = float(value)
        elif isinstance(value, str):
            number = float(value)
        else:
            return "—"
    except (TypeError, ValueError):
        return "—"
    if pct:
        return f"{number:+.1f}%"
    if money:
        if number >= 1_000_000:
            return f"${number / 1_000_000:.1f}M"
        if number >= 1_000:
            return f"${number / 1_000:.0f}K"
        return f"${number:,.0f}"
    return f"{number:.2f}"
