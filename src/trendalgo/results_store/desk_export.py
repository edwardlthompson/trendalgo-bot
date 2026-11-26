"""Composite desk surface export router (AV-G4–G7)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from trendalgo.results_store.desk_more import (
    load_about_surface,
    load_billing_surface,
    load_credman_surface,
    load_debug_surface,
    load_glossary_surface,
    load_notify_surface,
)
from trendalgo.results_store.desk_surfaces import (
    chart_summary_from_coin,
    enrich_strategy_row_metrics,
    find_coin,
    load_dex_surface,
    sauce_dossier_from_row,
    strategy_sheet_from_coin,
)


def needs_alpaca_cta(root: Path, lane: str) -> bool:
    del root
    key = str(lane or "crypto").strip().lower() or "crypto"
    if key == "crypto" or os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    from trendalgo.device.alpaca_vault import has_alpaca_credentials

    return not has_alpaca_credentials()


def _row_net(row: dict[str, Any]) -> float | None:
    for key in ("net_pct", "net", "return_pct", "gain"):
        raw = row.get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def load_backtest_surface(root: Path) -> dict[str, Any]:
    from trendalgo.device import strings as S
    from trendalgo.device.backtest_results_ui import filter_perfect_rows
    from trendalgo.device.backtest_row_filter import filter_rows
    from trendalgo.device.last_pair_backtest import load_last_pair_backtest
    from trendalgo.device.profile import read_json
    from trendalgo.device.results_view_prefs import load_results_prefs
    from trendalgo.device.views.market_context_format import (
        levels_lines,
        risk_line,
        signal_line,
        structure_lines,
    )

    prefs = load_results_prefs(root)
    saved = load_last_pair_backtest(root)
    raw_filters = read_json(root / "shell_backtest_filters.json")
    filters = raw_filters if isinstance(raw_filters, dict) else {}
    base = {
        "ok": True,
        "title": S.BACKTEST_TITLE,
        "subtitle": S.BACKTEST_SUBTITLE,
        "run_label": S.BACKTEST_RUN,
        "refresh_label": S.BACKTEST_REFRESH_PRICES,
        "refresh_tip": S.BACKTEST_REFRESH_PRICES_TIP,
        "perfect_label": S.BACKTEST_PERFECT_ONLY,
        "perfect_help": S.BACKTEST_PERFECT_HELP,
        "derive_label": S.BACKTEST_DERIVE_RULE,
        "status_label": S.SCANNER_STATUS,
        "share_label": S.BACKTEST_SHARE,
        "empty_title": S.BACKTEST_EMPTY_TITLE,
        "empty_body": S.BACKTEST_EMPTY_BODY,
        "strategy_caption": S.MARKET_CTX_STRATEGY_CAPTION,
        "perfect_only": prefs.perfect_only,
        "heatmap_enabled": prefs.heatmap_enabled,
        "market_context_collapsed": prefs.market_context_collapsed,
        "last_pair": prefs.last_pair,
        "filters": filters,
        "headers": list(S.BACKTEST_RESULT_HEADERS),
    }
    if saved is None:
        return {
            **base,
            "pair": prefs.last_pair or "",
            "rows": [],
            "market_context": {},
            "market_context_summary": {},
            "empty": True,
            "count": 0,
            "raw_count": 0,
        }
    pair, rows, ctx = saved
    shown = filter_perfect_rows(rows) if prefs.perfect_only else list(rows)
    shown = [enrich_strategy_row_metrics(r) for r in filter_rows(shown, filters)]
    shown.sort(key=lambda r: (_row_net(r) is not None, _row_net(r) or 0.0), reverse=True)
    summary: dict[str, str] = {}
    if isinstance(ctx, dict) and ctx:
        summary = {
            "signal": signal_line(ctx),
            "levels": "\n".join(levels_lines(ctx)),
            "risk": risk_line(ctx),
            "structure": "\n".join(structure_lines(ctx)),
        }
    return {
        **base,
        "pair": pair,
        "rows": shown,
        "market_context": ctx or {},
        "market_context_summary": summary,
        "empty": len(shown) == 0,
        "count": len(shown),
        "raw_count": len(rows),
    }


def load_dashboard_surface(root: Path) -> dict[str, Any]:
    from trendalgo.results_store.desk_dashboard import load_dashboard_surface as _load

    return _load(root)


def load_alerts_surface(root: Path, *, tab: str = "logs") -> dict[str, Any]:
    from trendalgo.device.scanner_alerts_store import history_for_tab, load_history

    all_rows = load_history(root)
    tab_key = str(tab or "logs").strip().lower() or "logs"
    rows = history_for_tab(all_rows, tab_key)
    return {"tab": tab_key, "rows": rows, "count": len(rows), "total": len(all_rows)}


def load_bots_surface(root: Path) -> dict[str, Any]:
    from trendalgo.device.plan_model import load_plan
    from trendalgo.device.profile import PLAN_FILE, ProfileError, read_json
    from trendalgo.results_store.bots_ops import load_live_bot_cards

    try:
        raw = read_json(root / PLAN_FILE)
        version, bots = load_plan(raw if isinstance(raw, dict) else None)
    except ProfileError:
        return {
            "version": 0,
            "rows": [],
            "cards": [],
            "count": 0,
            "host_badge": "local",
            "error": "bad_plan",
        }
    rows = [
        {
            "name": b.name,
            "pair": b.pair,
            "strategy": b.indicator,
            "timeframe": b.timeframe,
            "stake": b.stake_usd if b.stake_mode == "fixed_usd" else b.equity_pct,
            "id": "",
            "enabled": True,
            "state": "plan",
            "source": "plan.json",
        }
        for b in bots
    ]
    cards = load_live_bot_cards(root)
    from trendalgo.results_store.desk_host_badge import load_host_badge_surface

    badge = load_host_badge_surface(root)
    return {
        "version": version,
        "rows": rows,
        "cards": cards,
        "count": len(rows),
        "card_count": len(cards),
        "host_badge": badge.get("host_badge", "local"),
        "host_badge_label": badge.get("label", ""),
        "fab_label": "Add bot",
    }


def export_surface(root: Path, surface: str, *, lane: str, pair: str) -> dict[str, Any]:
    if surface == "alpaca":
        return {"lane": lane, "needs_cta": needs_alpaca_cta(root, lane)}
    if surface == "dex":
        return {"rows": load_dex_surface(root)}
    if surface == "backtest":
        return load_backtest_surface(root)
    if surface == "dashboard":
        return load_dashboard_surface(root)
    if surface == "alerts":
        return load_alerts_surface(root, tab=pair or "logs")
    if surface == "bots":
        return load_bots_surface(root)
    if surface == "bots_perf":
        from trendalgo.results_store.bots_ops import load_bots_performance_surface

        return load_bots_performance_surface(root)
    if surface == "bots_journal":
        from trendalgo.results_store.bots_ops import load_bots_journal_surface

        return load_bots_journal_surface(root)
    if surface == "buy_picks":
        from trendalgo.results_store.desk_board import load_buy_picks_surface

        return load_buy_picks_surface(root, lane=lane)
    if surface == "progress":
        from trendalgo.results_store.desk_progress import load_progress_surface

        return load_progress_surface(root, lane=lane)
    if surface == "glossary":
        return load_glossary_surface(query=pair)
    if surface == "debug":
        return load_debug_surface(root)
    if surface == "billing":
        return load_billing_surface()
    if surface == "about":
        return load_about_surface()
    if surface == "notify":
        return load_notify_surface(root)
    if surface == "credman":
        del root
        return load_credman_surface()
    if surface == "exchange_keys":
        from trendalgo.results_store.desk_exchange_keys import load_exchange_keys_surface

        return load_exchange_keys_surface(root)
    if surface == "venue":
        from trendalgo.results_store.desk_venue import load_execution_venue_surface

        return load_execution_venue_surface(root)
    if surface == "lanes":
        from trendalgo.results_store.desk_lanes import load_lanes_surface

        return load_lanes_surface(root)
    if surface == "connection":
        from trendalgo.results_store.desk_connection import load_connection_surface

        return load_connection_surface(root)
    if surface == "settings_layout":
        from trendalgo.results_store.desk_settings_layout import load_settings_layout_surface

        return load_settings_layout_surface(root)
    if surface == "wizard":
        from trendalgo.results_store.desk_wizard import load_wizard_surface

        return load_wizard_surface(root)
    if surface == "privacy":
        from trendalgo.results_store.desk_settings_misc import load_privacy_surface

        return load_privacy_surface(root)
    if surface == "data":
        from trendalgo.results_store.desk_settings_misc import load_data_surface

        return load_data_surface(root)
    if surface == "updates":
        from trendalgo.results_store.desk_settings_misc import load_updates_surface

        return load_updates_surface(root)
    if surface == "export_hub":
        from trendalgo.results_store.desk_export_hub import load_export_hub_surface

        return load_export_hub_surface(root)
    if surface == "host_badge":
        from trendalgo.results_store.desk_host_badge import load_host_badge_surface

        return load_host_badge_surface(root)
    if surface == "scan_settings":
        from trendalgo.results_store.scan_settings_surface import scan_settings_view

        return scan_settings_view(root)
    if surface == "startup":
        from trendalgo.results_store.desk_startup import load_startup_surface

        skip = (
            bool(os.environ.get("PYTEST_CURRENT_TEST"))
            or os.environ.get("TRENDALGO_STARTUP_SKIP_NET") == "1"
        )
        return load_startup_surface(root, skip_network=skip)
    coin = find_coin(root, pair, lane=lane) or {"pair": pair}
    if surface == "results":
        from trendalgo.device.views.market_context_format import (
            levels_lines,
            risk_line,
            signal_line,
            structure_lines,
        )

        raw_ctx = coin.get("market_context")
        ctx = raw_ctx if isinstance(raw_ctx, dict) else {}
        summary = {}
        if ctx:
            summary = {
                "signal": signal_line(ctx),
                "levels": "\n".join(levels_lines(ctx)),
                "risk": risk_line(ctx),
                "structure": "\n".join(structure_lines(ctx)),
            }
        return {
            "pair": pair,
            "rows": strategy_sheet_from_coin(coin),
            "market_context": ctx,
            "market_context_summary": summary,
        }
    if surface == "chart":
        if "|" in pair:
            raw_pair, window_key = pair.split("|", 1)
            chart_coin = find_coin(root, raw_pair, lane=lane) or {"pair": raw_pair}
            return chart_summary_from_coin(chart_coin, window_key=window_key)
        return chart_summary_from_coin(coin)
    if surface == "events":
        from trendalgo.results_store.desk_events import events_timeline_payload

        return events_timeline_payload(root, coin, pair)
    sheet = strategy_sheet_from_coin(coin)
    top = sheet[0] if sheet else {}
    return {"pair": pair, "dossier": sauce_dossier_from_row(top)}
