"""Headless smoke for Avalonia dual-runtime contracts (no GUI).

Exercises results.db + handshake + desk surfaces/share/enqueue the shell uses.
Exit 0 only when all checks pass.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from trendalgo.device.last_pair_backtest import save_last_pair_backtest
from trendalgo.device.lts_scan_model import load_lts_rows, save_lts_rows
from trendalgo.device.profile import profile_dir
from trendalgo.results_store.__main__ import main as store_main
from trendalgo.results_store.desk_commands import enqueue_command, peek_pending
from trendalgo.results_store.desk_export import export_surface
from trendalgo.results_store.desk_share import share_board_png, share_strategy_png
from trendalgo.results_store.desk_worker import process_pending
from trendalgo.results_store.ipc import PROTOCOL_VERSION, read_handshake
from trendalgo.results_store.schema import SCHEMA_VERSION
from trendalgo.results_store.store import ResultsStore

_SURFACES = (
    "results",
    "dex",
    "chart",
    "events",
    "sauce",
    "alpaca",
    "backtest",
    "dashboard",
    "alerts",
    "bots",
    "buy_picks",
    "progress",
    "glossary",
    "debug",
    "billing",
    "about",
    "notify",
)


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _ok(msg: str) -> None:
    print(f"OK {msg}")


def main() -> int:
    root = profile_dir()
    print(f"profile={root}")
    root.mkdir(parents=True, exist_ok=True)

    # Ensure handshake + demo workbook exist
    if store_main(["--root", str(root), "--demo"]) != 0:
        _fail("results_store --demo failed")

    hs = read_handshake(root)
    if hs is None:
        _fail("engine_ipc.json missing after demo")
    if not hs.compatible_with_shell(PROTOCOL_VERSION, SCHEMA_VERSION):
        _fail(f"handshake incompatible: {hs}")
    _ok(f"handshake engine={hs.engine_version} schema={hs.schema_version}")

    store = ResultsStore(root)
    try:
        run = store._conn.execute(
            "SELECT run_id, kind FROM runs WHERE kind='all_ta' ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        if run is None:
            _fail("no all_ta runs in results.db")
        run_id = str(run["run_id"])
        n = store.count_strategy_rows(run_id)
        if n < 1:
            _fail(f"all_ta run {run_id} has 0 strategy rows")
        page = list(store.iter_strategy_rows(run_id, limit=10))
        if len(page) < 1:
            _fail("iter_strategy_rows empty")
        _ok(f"workbook data run={run_id[:8]}… rows={n} sample={page[0].get('strategy_id')}")

        save_lts_rows(
            root,
            [
                {
                    "pair": "BTC/USD",
                    "symbol": "BTC",
                    "exchange": "kraken",
                    "gain": 3.5,
                    "volume_score": 1.2,
                    "health": "A",
                    "regime": "trend",
                    "score": 0.8,
                    "price": 42000.0,
                    "watch": True,
                },
                {
                    "pair": "ETH/USD",
                    "symbol": "ETH",
                    "exchange": "kraken",
                    "gain": 1.1,
                    "volume_score": 0.9,
                    "health": "B",
                },
            ],
            lane="crypto",
        )
        opp = store._conn.execute("SELECT COUNT(*) n FROM opportunity_rows").fetchone()["n"]
        if int(opp) < 1 and len(load_lts_rows(root)) < 1:
            _fail("LTS rows missing after save")
        _ok(f"opportunity bridge lts_json={len(load_lts_rows(root))} db_opp={opp}")

        save_last_pair_backtest(
            root,
            "ETH/USD",
            [{"strategy_id": "smoke-rsi", "pair": "ETH/USD", "net_pct": 3.0, "indicator": "RSI"}],
            market_context={"regime": "smoke", "bias": "long"},
        )
        n2 = store._conn.execute(
            "SELECT COUNT(*) n FROM strategy_rows WHERE strategy_id='smoke-rsi'"
        ).fetchone()["n"]
        if int(n2) < 1:
            _fail("bridge did not write smoke-rsi strategy row")
        _ok(f"strategy bridge smoke-rsi={n2}")
    finally:
        store.close()

    # Desk surfaces the shell Fetch()es
    for surface in _SURFACES:
        pair = "BTC/USD" if surface in {"results", "chart", "events", "sauce", "glossary"} else ""
        if surface == "alerts":
            pair = "logs"
        if surface == "glossary":
            pair = "rsi"
        data = export_surface(root, surface, lane="crypto", pair=pair)
        if not isinstance(data, dict):
            _fail(f"surface {surface} not a dict")
        _ok(f"surface {surface} keys={sorted(data.keys())[:6]}")

    # Share PNG board + strategy
    board = share_board_png(root, lane="crypto")
    board_path = Path(str(board["path"]))
    if not board_path.is_file() or board_path.stat().st_size < 50:
        _fail(f"board png missing/empty: {board_path}")
    _ok(f"share board png={board_path.name} bytes={board_path.stat().st_size}")

    strat = share_strategy_png(root, pair="BTC/USD", lane="crypto")
    strat_path = Path(str(strat["path"]))
    if not strat_path.is_file() or strat_path.stat().st_size < 50:
        _fail(f"strategy png missing/empty: {strat_path}")
    _ok(f"share strategy png={strat_path.name} bytes={strat_path.stat().st_size}")

    # Enqueue + desk-once dry publish
    cid = enqueue_command(root, "run_scan", lane="crypto")
    pending = peek_pending(root)
    if pending is None or pending.get("id") != cid:
        _fail("enqueue run_scan did not pend")
    result = process_pending(root, dry_run=True, batch_size=10)
    if result is None or result.get("status") not in {"done", "cancelled"}:
        _fail(f"desk-once dry failed: {result}")
    _ok(f"desk-once dry action={result['action']} rows={result.get('rows')}")

    # share_board via worker
    enqueue_command(root, "share_board", lane="crypto")
    share_result = process_pending(root, dry_run=True)
    if share_result is None or share_result.get("status") != "done":
        _fail(f"share_board desk-once failed: {share_result}")
    _ok("desk-once share_board")

    # Export path the shell uses
    exports = root / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    probe = exports / "smoke_avalonia.tsv"
    probe.write_text("strategy\tpair\tpayload\n", encoding="utf-8")
    _ok(f"exports writable {probe.name}")

    # Parity catalog + shell files for new features
    catalog = Path("shell/TrendAlgo.Shell/Models/ParityCatalog.cs")
    if not catalog.is_file():
        _fail("ParityCatalog.cs missing")
    text = catalog.read_text(encoding="utf-8")
    for needle in ('"crypto"', '"tradfi"', '"forex"', '"workbook"', '"settings"', '"billing"'):
        if needle not in text:
            _fail(f"ParityCatalog missing {needle}")
    _ok("parity catalog desks")

    for rel in (
        "shell/TrendAlgo.Shell/Services/ShellTray.cs",
        "shell/TrendAlgo.Shell/Views/WizardWindow.axaml",
        "shell/TrendAlgo.Shell/Views/FeedbackWindow.axaml",
        "shell/TrendAlgo.Shell/Services/WindowGeometryStore.cs",
        "shell/TrendAlgo.Shell/Services/DeskSurfaceClient.cs",
    ):
        if not Path(rel).is_file():
            _fail(f"missing {rel}")
    _ok("shell tray/wizard/feedback/geometry present")

    axaml = Path("shell/TrendAlgo.Shell/Views/MainWindow.axaml").read_text(encoding="utf-8")
    for needle in (
        "DeskForceFreshCommand",
        "ShareStrategyPngCommand",
        "OpenFeedbackCommand",
        "BotsToggleHostPollCommand",
        "SelectDashboardRangeCommand",
        "ShowNotifyMatrix",
        "GlossarySearchCommand",
    ):
        if needle not in axaml:
            _fail(f"MainWindow.axaml missing {needle}")
    _ok("MainWindow wires gap-depth commands")

    gaps = Path("docs/AVALONIA_PARITY_GAPS.md").read_text(encoding="utf-8")
    if "- [ ]" in gaps:
        _fail("AVALONIA_PARITY_GAPS still has open [ ] items")
    _ok("parity gaps checklist fully checked")

    ipc = json.loads((root / "engine_ipc.json").read_text(encoding="utf-8"))
    _ok(f"ipc json keys {sorted(ipc.keys())}")
    print("SMOKE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
