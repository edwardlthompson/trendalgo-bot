"""Write handshake, demo rows, or enqueue Avalonia desk commands (AV-G1)."""

from __future__ import annotations

import argparse
import json
import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from trendalgo.device.profile import profile_dir
from trendalgo.results_store.desk_cli_extra import print_json, run_mutate, run_share_png
from trendalgo.results_store.desk_commands import STRIP_ACTIONS, enqueue_command
from trendalgo.results_store.desk_export import export_surface
from trendalgo.results_store.desk_worker import drain_pending
from trendalgo.results_store.ipc import handshake_payload, write_handshake
from trendalgo.results_store.schema import RESULTS_DB, SCHEMA_VERSION
from trendalgo.results_store.store import ResultsStore

_SURFACES = (
    "results,dex,chart,events,sauce,alpaca,backtest,dashboard,"
    "alerts,bots,bots_perf,bots_journal,buy_picks,progress,glossary,debug,billing,"
    "about,notify,credman,exchange_keys,scan_settings,startup,venue,lanes,connection,"
    "settings_layout,wizard,privacy,data,updates,export_hub,host_badge"
).split(",")


def _engine_version() -> str:
    try:
        return version("trendalgo-bot")
    except PackageNotFoundError:
        return "0.0.0-dev"


def _write_hs(root: Path) -> None:
    write_handshake(
        root,
        handshake_payload(
            engine_version=_engine_version(),
            schema_version=SCHEMA_VERSION,
            catalog_hash=os.environ.get("TRENDALGO_CATALOG_HASH", ""),
            results_db=RESULTS_DB,
            pid=os.getpid(),
        ),
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="TrendAlgo results.db / desk IPC (ADR-0021)")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--migrate-lts", action="store_true")
    p.add_argument("--root", type=Path, default=None)
    p.add_argument("--enqueue", choices=sorted(STRIP_ACTIONS), default=None)
    p.add_argument("--lane", default="crypto")
    p.add_argument("--lanes", default="")
    p.add_argument("--autoscan", type=int, choices=(0, 1), default=None)
    p.add_argument("--desk-once", action="store_true")
    p.add_argument("--desk-dry", action="store_true")
    p.add_argument("--surface", choices=_SURFACES, default=None)
    p.add_argument("--pair", default="")
    p.add_argument("--toggle-watch", action="store_true")
    p.add_argument("--create-bot", action="store_true")
    p.add_argument("--indicator", default="RSI")
    p.add_argument("--force-fresh", action="store_true")
    p.add_argument("--share-png", choices=("board", "strategy", "dashboard"), default=None)
    p.add_argument("--dest", type=Path, default=None, help="PNG output path for --share-png")
    p.add_argument(
        "--pairs",
        default="",
        help="Comma-separated pairs for --share-png board (visible list order)",
    )
    p.add_argument("--share-title", default="", help="Title for --share-png board")
    p.add_argument(
        "--filters-json",
        type=Path,
        default=None,
        help="JSON object of active board filters for --share-png board caption",
    )
    p.add_argument(
        "--include-mc",
        type=int,
        choices=(0, 1),
        default=1,
        help="Include Market Context band on board PNG (0 when MC collapsed)",
    )
    p.add_argument("--apply-scan-settings", type=Path, default=None)
    p.add_argument("--apply-dashboard-customize", type=Path, default=None)
    p.add_argument("--apply-dashboard-mins", type=Path, default=None)
    p.add_argument("--apply-dashboard-layout", type=Path, default=None)
    p.add_argument("--verify-exchange-key", default=None)
    p.add_argument("--portfolio-sync", action="store_true")
    p.add_argument("--export-portfolio-report", type=Path, default=None)
    p.add_argument("--bots-panic", action="store_true")
    p.add_argument("--bots-publish-plan", action="store_true")
    p.add_argument("--bots-set-enabled", default=None, help="bot_id for --bots-enable/--bots-pause")
    p.add_argument("--bots-enable", action="store_true")
    p.add_argument("--bots-pause", action="store_true")
    p.add_argument("--derive-oracle", action="store_true")
    p.add_argument("--apply-venue", type=Path, default=None)
    p.add_argument("--apply-lanes", type=Path, default=None)
    p.add_argument("--apply-connection", type=Path, default=None)
    p.add_argument("--apply-settings-layout", type=Path, default=None)
    p.add_argument("--wizard-advance", type=Path, default=None)
    p.add_argument("--wizard-back", action="store_true")
    p.add_argument("--apply-privacy", type=Path, default=None)
    p.add_argument("--apply-data", type=Path, default=None)
    p.add_argument("--check-updates", action="store_true")
    p.add_argument("--export-hub", type=Path, default=None)
    p.add_argument("--apply-results-prefs", type=Path, default=None)
    p.add_argument("--test-telegram", action="store_true")
    p.add_argument("--test-telegram-rich", action="store_true")
    p.add_argument("--test-grokbot", action="store_true")
    p.add_argument("--benchmark", action="store_true")
    p.add_argument("--pair-backtest", action="store_true")
    p.add_argument("--sidecar", action="store_true")
    p.add_argument(
        "--ack-startup",
        choices=("clear_crash", "donate", "update"),
        default=None,
        help="Persist startup dialog ack (crash clear / donate seen / update check)",
    )
    p.add_argument("--ack-version", default="", help="Version for --ack-startup")
    p.add_argument(
        "--ack-dismissed",
        action="store_true",
        help="With --ack-startup update: mark dismissed_version",
    )
    args = p.parse_args(argv)
    root = args.root or profile_dir()
    root.mkdir(parents=True, exist_ok=True)
    _write_hs(root)

    if args.sidecar:
        from trendalgo.results_store.sidecar import run_sidecar

        return run_sidecar(root)
    if args.benchmark:
        from trendalgo.results_store.scan_benchmark import run_quick_benchmark

        print(json.dumps(run_quick_benchmark(root)))
        return 0
    if args.pair_backtest:
        from trendalgo.results_store.desk_jobs import run_pair_backtest_direct

        print(json.dumps(run_pair_backtest_direct(root, args.pair, args.lane)))
        return 0
    if args.bots_panic:
        from trendalgo.results_store.bots_ops import run_bots_panic

        print(json.dumps(run_bots_panic(root)))
        return 0
    if args.bots_publish_plan:
        from trendalgo.results_store.bots_ops import publish_plan_to_host

        result = publish_plan_to_host(root)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.bots_set_enabled is not None and (args.bots_enable or args.bots_pause):
        from trendalgo.results_store.bots_ops import set_bot_enabled

        result = set_bot_enabled(root, args.bots_set_enabled, enabled=bool(args.bots_enable))
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.derive_oracle:
        from trendalgo.results_store.desk_oracle_derive import derive_oracle_rule

        result = derive_oracle_rule(root, pair=args.pair, lane=args.lane)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.apply_venue is not None:
        from trendalgo.results_store.desk_venue import apply_execution_venue

        payload = json.loads(args.apply_venue.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = apply_execution_venue(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.apply_lanes is not None:
        from trendalgo.results_store.desk_lanes import apply_lanes_settings

        payload = json.loads(args.apply_lanes.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = apply_lanes_settings(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.apply_connection is not None:
        from trendalgo.results_store.desk_connection import apply_connection_settings

        payload = json.loads(args.apply_connection.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = apply_connection_settings(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.apply_settings_layout is not None:
        from trendalgo.results_store.desk_settings_layout import apply_settings_layout

        payload = json.loads(args.apply_settings_layout.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = apply_settings_layout(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.wizard_advance is not None:
        from trendalgo.results_store.desk_wizard import advance_wizard

        payload = json.loads(args.wizard_advance.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = advance_wizard(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.wizard_back:
        from trendalgo.results_store.desk_wizard import rewind_wizard

        result = rewind_wizard(root)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.apply_privacy is not None:
        from trendalgo.results_store.desk_settings_misc import apply_privacy_settings

        payload = json.loads(args.apply_privacy.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = apply_privacy_settings(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.apply_data is not None:
        from trendalgo.results_store.desk_settings_misc import apply_data_settings

        payload = json.loads(args.apply_data.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = apply_data_settings(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.check_updates:
        from trendalgo.results_store.desk_settings_misc import check_updates_now

        result = check_updates_now(root)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.export_hub is not None:
        from trendalgo.results_store.desk_export_hub import run_export_hub

        payload = json.loads(args.export_hub.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = run_export_hub(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.apply_results_prefs is not None:
        from trendalgo.results_store.desk_results_prefs import apply_results_prefs

        payload = json.loads(args.apply_results_prefs.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = apply_results_prefs(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.test_telegram or args.test_telegram_rich or args.test_grokbot:
        from trendalgo.results_store.notify_test import (
            send_grokbot_test,
            send_telegram_rich_preview,
            send_telegram_test,
        )

        if args.test_telegram_rich:
            result = send_telegram_rich_preview(root)
        elif args.test_telegram:
            result = send_telegram_test(root)
        else:
            result = send_grokbot_test(root)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.ack_startup is not None:
        from trendalgo.results_store.desk_startup import ack_startup_prompt

        print(
            json.dumps(
                ack_startup_prompt(
                    root,
                    kind=args.ack_startup,
                    version=args.ack_version,
                    current_version=args.ack_version or _engine_version(),
                    dismissed=bool(args.ack_dismissed),
                )
            )
        )
        return 0
    if args.apply_scan_settings is not None:
        from trendalgo.results_store.scan_settings_surface import apply_scan_settings

        payload = json.loads(args.apply_scan_settings.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = apply_scan_settings(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.apply_dashboard_customize is not None:
        from trendalgo.results_store.desk_dashboard import apply_dashboard_customize

        payload = json.loads(args.apply_dashboard_customize.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = apply_dashboard_customize(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.apply_dashboard_mins is not None:
        from trendalgo.results_store.desk_dashboard import apply_dashboard_module_mins

        payload = json.loads(args.apply_dashboard_mins.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = apply_dashboard_module_mins(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.apply_dashboard_layout is not None:
        from trendalgo.results_store.desk_dashboard import apply_dashboard_layout

        payload = json.loads(args.apply_dashboard_layout.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = apply_dashboard_layout(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.verify_exchange_key is not None:
        from trendalgo.results_store.desk_exchange_keys import verify_saved_exchange_key

        result = verify_saved_exchange_key(root, args.verify_exchange_key)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.portfolio_sync:
        from trendalgo.results_store.desk_portfolio_sync import run_live_portfolio_sync

        result = run_live_portfolio_sync(root)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.export_portfolio_report is not None:
        from trendalgo.portfolio.report_export import run_portfolio_report_export

        payload = json.loads(args.export_portfolio_report.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            print(json.dumps({"ok": False, "error": "payload_not_object"}))
            return 1
        result = run_portfolio_report_export(root, payload)
        print(json.dumps(result))
        return 0 if result.get("ok") else 1
    if args.enqueue:
        params: dict[str, object] = {}
        if args.enqueue == "set_autoscan" and args.autoscan is not None:
            params["enabled"] = bool(args.autoscan)
        if args.enqueue == "run_scan" and args.force_fresh:
            params["force_fresh"] = True
        if args.enqueue == "run_backtest" and args.pair.strip():
            params["pair"] = args.pair.strip().upper()
        if args.enqueue == "run_all_scans" and args.lanes.strip():
            params["lanes"] = [ln.strip().lower() for ln in args.lanes.split(",") if ln.strip()]
        cid = enqueue_command(root, args.enqueue, lane=args.lane, params=params)
        print(f"enqueued id={cid} action={args.enqueue} lane={args.lane}")
        return 0
    if args.toggle_watch or args.create_bot:
        print_json(
            run_mutate(
                root,
                toggle_watch=bool(args.toggle_watch),
                pair=args.pair,
                lane=args.lane,
                indicator=args.indicator,
            )
        )
        return 0
    if args.share_png:
        pair_list = [p.strip() for p in str(args.pairs or "").split(",") if p.strip()]
        filters_payload: dict[str, object] | None = None
        if args.filters_json is not None and Path(args.filters_json).is_file():
            raw = json.loads(Path(args.filters_json).read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                filters_payload = raw
        print_json(
            run_share_png(
                root,
                args.share_png,
                lane=args.lane,
                pair=args.pair,
                dest=args.dest,
                pairs=pair_list or None,
                title=str(args.share_title or "").strip() or None,
                filters=filters_payload,
                include_market_context=bool(args.include_mc),
            )
        )
        return 0
    if args.desk_once:
        from trendalgo.device.lock import ProfileBusyError, ProfileLock

        # Single-flight: Avalonia used to spawn overlapping --desk-once workers that
        # starved crypto All-TA and left zombie multiprocessing children.
        desk_lock = ProfileLock(root / "desk_once.lock")
        try:
            desk_lock.acquire()
        except ProfileBusyError:
            print("desk-once: busy (another desk-once already running)")
            return 0
        try:
            pending = drain_pending(root, dry_run=bool(args.desk_dry))
            if pending is None:
                print("desk-once: idle (no pending)")
                return 0
            print(
                f"desk-once action={pending['action']} status={pending['status']} "
                f"rows={pending['rows']} run_id={pending['run_id']}"
            )
            return 0 if pending["status"] in {"done", "cancelled"} else 1
        finally:
            desk_lock.release()
    if args.surface:
        print(json.dumps(export_surface(root, args.surface, lane=args.lane, pair=args.pair)))
        return 0

    store = ResultsStore(root)
    if args.migrate_lts:
        store.migrate_opportunity_json(root / "lts_scan_rows.json")
    if args.demo:
        run_id = store.start_run(
            "all_ta", lane="crypto", pair="BTC/USD", engine_version=_engine_version()
        )
        store.set_job_state("demo", "running", run_id=run_id)
        store.append_strategy_rows(
            run_id,
            [
                {"strategy_id": f"demo-{i:03d}", "pair": "BTC/USD", "score": float(i)}
                for i in range(50)
            ],
        )
        store.set_job_state("demo", "done", run_id=run_id)
        store.finish_run(run_id)
        print(f"demo run_id={run_id} rows=50 path={store.path}")
    else:
        print(f"handshake ok schema={SCHEMA_VERSION} path={store.path}")
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
