"""Export hub: journal CSV / plan JSON / scan JSON (AV-G-OTH1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device import strings as S
from trendalgo.device.export_model import (
    default_export_dir,
    write_journal_csv,
    write_plan_json,
    write_scan_json,
)
from trendalgo.device.profile import PLAN_FILE, db_paths

__all__ = ["load_export_hub_surface", "run_export_hub"]


def load_export_hub_surface(root: Path) -> dict[str, Any]:
    dest = default_export_dir(root)
    dest.mkdir(parents=True, exist_ok=True)
    return {
        "ok": True,
        "title": S.EXPORT_TITLE,
        "subtitle": S.EXPORT_SUBTITLE,
        "folder_help": S.EXPORT_FOLDER_HELP,
        "folder": str(dest),
        "folder_label": S.EXPORT_FOLDER_LABEL.format(path=dest),
        "choose_label": S.EXPORT_CHOOSE_FOLDER,
        "journal_label": S.EXPORT_JOURNAL,
        "plan_label": S.EXPORT_PLAN,
        "scan_label": S.EXPORT_SCAN,
        "actions": [
            {"id": "journal", "label": S.EXPORT_JOURNAL},
            {"id": "plan", "label": S.EXPORT_PLAN},
            {"id": "scan", "label": S.EXPORT_SCAN},
        ],
        "portfolio_actions": [
            {"id": "portfolio_html", "label": "Executive Portfolio Report (HTML / PDF)"},
            {"id": "portfolio_csv", "label": "Holdings & Equity CSV Bundle"},
        ],
    }


def run_export_hub(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    kind = str(payload.get("kind") or "").strip().lower()
    dest_raw = str(payload.get("dest") or "").strip()
    dest = Path(dest_raw) if dest_raw else default_export_dir(root)
    dbs = db_paths(root)
    try:
        if kind == "journal":
            path = write_journal_csv(dest, dbs["journal"])
        elif kind == "plan":
            path = write_plan_json(dest, root / PLAN_FILE)
        elif kind == "scan":
            path = write_scan_json(dest, dbs["scanner"])
        elif kind == "portfolio_html":
            from trendalgo.portfolio.report_export import export_portfolio_html_report

            path = export_portfolio_html_report(root, dest=dest if dest.suffix else None)
        elif kind == "portfolio_csv":
            from trendalgo.portfolio.report_export import export_portfolio_csv_bundle

            bundle = export_portfolio_csv_bundle(root, dest_dir=dest)
            path = Path(bundle["holdings_csv"])
        else:
            return {"ok": False, "error": "bad_kind", "problems": [f"Unknown export kind: {kind}"]}
    except FileNotFoundError:
        missing = {
            "journal": S.EXPORT_NO_JOURNAL,
            "plan": S.EXPORT_NO_PLAN,
            "scan": S.EXPORT_NO_SCAN,
        }.get(kind, "Nothing to export")
        return {"ok": False, "error": "missing", "problems": [missing]}
    except OSError as exc:
        return {"ok": False, "error": "os", "problems": [str(exc)]}
    return {
        "ok": True,
        "kind": kind,
        "path": str(path),
        "name": path.name,
        "message": S.EXPORT_DONE.format(name=path.name, path=path),
        "folder": str(dest),
    }
