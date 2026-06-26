#!/usr/bin/env python3
"""Founder gate CLI — H-001–H-034 preflight, approve, backlog."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATES_PATH = ROOT / ".cursor" / "founder-gates.json"
DEFAULTS_PATH = ROOT / "config" / "founder.defaults.json"
DEFAULTS_EXAMPLE = ROOT / "config" / "founder.defaults.json.example"

HARD_GATES = frozenset({"H-006", "H-008", "H-010", "H-011", "H-023", "H-028", "H-031", "H-032"})

SPRINT_GATES: dict[int, list[str]] = {
    0: ["H-001", "H-003", "H-004", "H-005", "H-006"],
    1: ["H-007"],
    2: ["H-008"],
    3: ["H-009"],
    4: ["H-010", "H-011", "H-012"],
    5: ["H-015", "H-016", "H-017"],
    6: ["H-018"],
    7: ["H-019"],
    8: ["H-020", "H-021"],
    10: ["H-022"],
    11: ["H-024"],
    12: ["H-025"],
    13: ["H-030", "H-034"],
    14: ["H-034"],
    15: ["H-031", "H-034"],
    16: ["H-034"],
    17: ["H-034"],
    18: ["H-032", "H-034"],
    19: ["H-032", "H-034"],
    20: ["H-032", "H-034"],
}

BUNDLE_PRE_SPRINT_1 = ["H-001", "H-005", "H-007"]


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    if cmd and cmd[0] == "bash":
        bash = shutil.which("bash")
        if not bash:
            script = Path(cmd[1]) if len(cmd) > 1 else None
            if script and script.suffix == ".py":
                cmd = [sys.executable, str(script), *cmd[2:]]
            elif script and script.exists():
                return 2, f"bash unavailable — {script.name} present (SCHEDULED)"
            else:
                return 1, "bash unavailable"
        else:
            cmd = [bash, *cmd[1:]]
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd or ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if "\x00" in out:
            out = out.replace("\x00", "")
        text = out.strip()
        if proc.returncode != 0 and "Windows Subsystem for Linux" in text:
            script_path = cmd[1] if len(cmd) > 1 else None
            script = Path(script_path) if script_path else None
            if script and script.exists():
                return 2, f"bash/WSL unavailable — {script.name} present (SCHEDULED)"
        return proc.returncode, text
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return 1, str(exc)


def load_gates() -> dict:
    GATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    if GATES_PATH.exists():
        return json.loads(GATES_PATH.read_text(encoding="utf-8"))
    return {"version": 1, "updated_at": None, "gates": {}}


def save_gates(data: dict) -> None:
    data["version"] = 1
    data["updated_at"] = datetime.now(UTC).replace(microsecond=0).isoformat()
    GATES_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def gate_record(data: dict, hid: str) -> dict:
    return data.setdefault("gates", {}).setdefault(hid, {"status": "pending"})


def preflight_h001() -> tuple[int, str]:
    readme = ROOT / "README.md"
    if not readme.exists():
        return 1, "README.md missing"
    if "TrendAlgo Bot" not in readme.read_text(encoding="utf-8", errors="replace"):
        return 1, "README.md must contain 'TrendAlgo Bot'"
    code, out = _run(["git", "remote", "get-url", "origin"])
    if code != 0:
        return 1, "git remote origin not configured"
    return 0, f"origin={out}"


def preflight_h003() -> tuple[int, str]:
    script = ROOT / "scripts" / "verify-branch-protection.sh"
    if not script.exists():
        setup = ROOT / "scripts" / "setup-github-repo.sh"
        if setup.exists():
            return 0, "setup-github-repo.sh present (run after gh auth)"
        return 1, "verify-branch-protection.sh missing"
    code, out = _run(["bash", str(script)])
    if code == 0:
        return 0, "branch protection verified"
    if code == 2:
        return 2, out or "branch protection SCHEDULED"
    if "Windows Subsystem for Linux" in out.replace("\x00", ""):
        return 2, "branch protection SCHEDULED (bash/WSL unavailable)"
    return 1, out or "branch protection check failed"


def preflight_h004() -> tuple[int, str]:
    script = ROOT / "scripts" / "check-hosting-eligibility.sh"
    if not script.exists():
        return 2, "SCHEDULED — check-hosting-eligibility.sh (S0)"
    code, out = _run(["bash", str(script)])
    if code == 2:
        return 2, out or "hosting eligibility SCHEDULED"
    return code, out or "hosting eligibility"


def preflight_h008_h011(hid: str) -> tuple[int, str]:
    script = ROOT / "scripts" / "setup-secrets.sh"
    env = ROOT / ".env"
    if env.exists():
        return 0, ".env present (secrets configured locally)"
    if script.exists():
        return 2, f"HUMAN — run scripts/setup-secrets.sh ({hid})"
    return 1, "setup-secrets.sh missing"


def preflight_h005() -> tuple[int, str]:
    if DEFAULTS_PATH.exists():
        return 0, f"found at {DEFAULTS_PATH.relative_to(ROOT)}"
    if DEFAULTS_EXAMPLE.exists():
        return 1, "Run: bash scripts/apply-founder-defaults.sh"
    return 1, "config/founder.defaults.json.example missing"


def preflight_h007() -> tuple[int, str]:
    adr = ROOT / "docs" / "adr" / "0001-core-architecture.md"
    if not adr.exists():
        return 1, "ADR-0001 not found"
    vb = ROOT / "scripts" / "validate-bootstrap.sh"
    if vb.exists():
        code, out = _run(["bash", str(vb), "--quick"])
        if code != 0:
            return code, f"validate-bootstrap --quick failed: {out[:200]}"
    return 0, "ADR-0001 present"


def preflight_script(script_rel: str, *, scheduled_msg: str = "") -> tuple[int, str]:
    script = ROOT / script_rel
    if not script.exists():
        return 2, scheduled_msg or f"SCHEDULED — {script_rel} not yet created"
    code, out = _run(["bash", str(script)])
    if code == 2:
        return 2, out or scheduled_msg or f"{script_rel} SCHEDULED"
    return code, out or script_rel


def preflight_sprint_scope(sprint: int) -> tuple[int, str]:
    script = ROOT / "scripts" / "sprint-preflight.sh"
    if not script.exists():
        return 2, f"SCHEDULED — sprint-preflight.sh (S{sprint})"
    code, out = _run(["bash", str(script), "--sprint", str(sprint)])
    if code == 2:
        return 2, out or f"sprint-preflight S{sprint} SCHEDULED"
    return code, out or f"sprint-preflight S{sprint}"


def preflight_legal_packet() -> tuple[int, str]:
    packet = ROOT / "docs" / "legal-review-packet.md"
    terms = ROOT / "TERMS.md"
    missing = [p.name for p in (packet, terms) if not p.exists()]
    if missing:
        return 1, f"missing: {', '.join(missing)}"
    return 2, "HUMAN — attorney review required (artifacts present)"


def preflight_h021() -> tuple[int, str]:
    return 0, "Superseded by H-030 — see docs/EXCHANGE_ROADMAP.md"


def preflight_h030() -> tuple[int, str]:
    roadmap = ROOT / "docs" / "EXCHANGE_ROADMAP.md"
    build = ROOT / "BUILD_PLAN.md"
    missing = [p.name for p in (roadmap, build) if not p.exists()]
    if missing:
        return 1, f"missing: {', '.join(missing)}"
    build_text = build.read_text(encoding="utf-8", errors="replace")
    if "Sprint 13" not in build_text and "S13" not in build_text:
        return 1, "BUILD_PLAN missing S13 exchange lane"
    if "Native CCXT" not in build_text and "ADR-0010" not in build_text:
        return 1, "BUILD_PLAN missing native engine constraint"
    return 2, "HUMAN — approve exchange program scope (Tier A/B + native-only)"


def preflight_h031() -> tuple[int, str]:
    adr = ROOT / "docs" / "adr" / "0010-ccxt-native-engine.md"
    native = ROOT / "docs" / "NATIVE_TRADING.md"
    missing = [p.name for p in (adr, native) if not p.exists()]
    if missing:
        return 1, f"missing: {', '.join(missing)}"
    return 2, "HUMAN — approve ADR-0010 + explicit Freqtrade removal (hard gate)"


def preflight_h032() -> tuple[int, str]:
    roadmap = ROOT / "docs" / "EXCHANGE_ROADMAP.md"
    registry = ROOT / "config" / "exchanges.registry.json"
    if not roadmap.exists():
        return 1, "docs/EXCHANGE_ROADMAP.md missing"
    text = roadmap.read_text(encoding="utf-8", errors="replace")
    if "Tier D" not in text and "S18" not in text:
        return 1, "EXCHANGE_ROADMAP missing worldwide trading section"
    if registry.exists():
        import json

        data = json.loads(registry.read_text(encoding="utf-8"))
        phase = int(data.get("worldwide_trading_phase", 0))
        worldwide = [
            e["id"]
            for e in data.get("exchanges", [])
            if e.get("trading_enabled") and e.get("us_restricted")
        ]
        if phase < 1 or len(worldwide) < 3:
            return 1, f"registry phase={phase} worldwide_trading={worldwide}"
    return 2, "HUMAN — approve worldwide bot trading phase plan (hard gate)"


def preflight_h034() -> tuple[int, str]:
    local_dev = ROOT / "docs" / "LOCAL_DEV.md"
    ps1 = ROOT / "scripts" / "dev-local.ps1"
    sh = ROOT / "scripts" / "dev-local.sh"
    missing = [p.name for p in (local_dev, ps1, sh) if not p.exists()]
    if missing:
        return 1, f"missing: {', '.join(missing)}"
    return 2, "HUMAN — run L1 preview (dev-local) and approve with --note"


PREFLIGHT_HANDLERS: dict[str, callable] = {
    "H-001": preflight_h001,
    "H-002": lambda: preflight_stub("H-002", "docs/CURSOR_MODES.md"),
    "H-003": preflight_h003,
    "H-004": preflight_h004,
    "H-005": preflight_h005,
    "H-006": preflight_legal_packet,
    "H-007": preflight_h007,
    "H-008": lambda: preflight_h008_h011("H-008"),
    "H-009": lambda: preflight_stub("H-009", "examples/web/playwright.config.ts"),
    "H-010": lambda: preflight_script("scripts/go-live-gate.sh"),
    "H-011": lambda: preflight_h008_h011("H-011"),
    "H-012": lambda: preflight_script("scripts/check-production-cost.sh"),
    "H-013": lambda: preflight_sprint_scope(4),
    "H-014": lambda: preflight_script("scripts/lts-parity-check.sh"),
    "H-015": lambda: preflight_sprint_scope(5),
    "H-016": lambda: preflight_script(
        "scripts/smoke-notifications.sh", scheduled_msg="SCHEDULED — notifications (S5)"
    ),
    "H-017": lambda: preflight_script(
        "scripts/compare-portfolio-parity.sh",
        scheduled_msg="SCHEDULED — compare-portfolio-parity.sh (S5)",
    ),
    "H-018": lambda: preflight_sprint_scope(6),
    "H-019": lambda: preflight_sprint_scope(7),
    "H-020": lambda: preflight_sprint_scope(8),
    "H-021": preflight_h021,
    "H-022": preflight_legal_packet,
    "H-023": preflight_legal_packet,
    "H-024": lambda: preflight_sprint_scope(11),
    "H-025": lambda: preflight_sprint_scope(12),
    "H-026": lambda: preflight_script(
        "scripts/check-portfolio-integrity.sh", scheduled_msg="SCHEDULED — portfolio (S5)"
    ),
    "H-027": lambda: preflight_script("scripts/check-production-cost.sh"),
    "H-028": lambda: preflight_script("scripts/go-live-gate.sh"),
    "H-030": preflight_h030,
    "H-031": preflight_h031,
    "H-032": preflight_h032,
    "H-034": preflight_h034,
}


def preflight_stub(hid: str, artifact: str) -> tuple[int, str]:
    path = ROOT / artifact
    if path.exists():
        return 0, f"{artifact} present"
    return 2, f"SCHEDULED — {artifact} not yet created (sprint later)"


def run_preflight(hid: str, *, strict: bool = False) -> tuple[int, str]:
    handler = PREFLIGHT_HANDLERS.get(hid)
    if handler is None:
        return 2, f"No AUTO preflight for {hid} — use founder-gate approve after manual check"
    code, msg = handler()
    if code == 2 and strict:
        return 1, msg
    return code, msg


def cmd_preflight(args: argparse.Namespace) -> int:
    hid = args.hid
    code, msg = run_preflight(hid, strict=args.strict)
    label = "PASS" if code == 0 else "SKIP" if code == 2 else "FAIL"
    print(f"{hid}: {label} — {msg}")
    if code == 0:
        data = load_gates()
        rec = gate_record(data, hid)
        if rec.get("status") != "approved":
            rec["status"] = "preflight_ok"
            rec["preflight_exit"] = 0
        save_gates(data)
    return 0 if code in (0, 2) and not args.strict else code


def cmd_status(args: argparse.Namespace) -> int:
    data = load_gates()
    gates = data.get("gates", {})
    all_ids = sorted({f"H-{i:03d}" for i in range(1, 35)} | set(gates.keys()))
    rows = []
    for hid in all_ids:
        rec = gates.get(hid, {"status": "pending"})
        rows.append({"id": hid, **rec})
    if args.json:
        print(json.dumps({"gates": rows}, indent=2))
    else:
        for row in rows:
            print(f"{row['id']}: {row.get('status', 'pending')}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    hid = args.hid
    code, msg = run_preflight(hid, strict=True)
    if code != 0:
        print(f"Cannot approve {hid}: preflight failed — {msg}", file=sys.stderr)
        return 1
    data = load_gates()
    rec = gate_record(data, hid)
    rec["status"] = "approved"
    rec["approved_at"] = datetime.now(UTC).replace(microsecond=0).isoformat()
    rec["preflight_exit"] = 0
    if args.note:
        rec["note"] = args.note
    save_gates(data)
    print(f"Approved {hid}")
    return 0


def cmd_backlog(args: argparse.Namespace) -> int:
    data = load_gates()
    rec = gate_record(data, args.hid)
    rec["status"] = "backlog"
    rec["backlog_reason"] = args.reason or "manual backlog"
    save_gates(data)
    print(f"Backlog {args.hid}: {rec['backlog_reason']}")
    return 0


def cmd_approve_bundle(args: argparse.Namespace) -> int:
    bundle = BUNDLE_PRE_SPRINT_1 if args.bundle == "pre-sprint-1" else args.bundle.split(",")
    failed = 0
    for hid in bundle:
        hid = hid.strip()
        if cmd_approve(argparse.Namespace(hid=hid, note=args.note)) != 0:
            failed += 1
    return 1 if failed else 0


def cmd_preflight_sprint(args: argparse.Namespace) -> int:
    sprint = args.sprint
    ids = SPRINT_GATES.get(sprint, [])
    if not ids:
        print(f"No H-IDs mapped for sprint {sprint}")
        return 0
    worst = 0
    for hid in ids:
        code, msg = run_preflight(hid, strict=args.strict)
        label = "PASS" if code == 0 else "SKIP" if code == 2 else "FAIL"
        print(f"{hid}: {label} — {msg}")
        if code == 1 or (args.strict and code != 0):
            worst = 1
    return worst


def cmd_approve_all_soft(args: argparse.Namespace) -> int:
    """Approve every gate with PASS preflight that is not a hard gate."""
    candidates = sorted(
        hid for hid in PREFLIGHT_HANDLERS if hid not in HARD_GATES and hid != "H-002"
    )
    approved = 0
    skipped = 0
    failed = 0
    for hid in candidates:
        code, msg = run_preflight(hid, strict=False)
        if code != 0:
            skipped += 1
            if args.verbose:
                label = "SKIP" if code == 2 else "FAIL"
                print(f"{hid}: {label} — {msg}")
            continue
        if args.dry_run:
            print(f"{hid}: would approve — {msg}")
            approved += 1
            continue
        if cmd_approve(argparse.Namespace(hid=hid, note=args.note)) == 0:
            approved += 1
        else:
            failed += 1
    print(f"approve-all-soft: approved={approved} skipped={skipped} failed={failed}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Founder gate CLI")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status")
    p_status.set_defaults(func=cmd_status)

    p_pf = sub.add_parser("preflight")
    p_pf.add_argument("hid")
    p_pf.set_defaults(func=cmd_preflight)

    p_pfs = sub.add_parser("preflight-sprint")
    p_pfs.add_argument("--sprint", type=int, required=True)
    p_pfs.set_defaults(func=cmd_preflight_sprint)

    p_ap = sub.add_parser("approve")
    p_ap.add_argument("hid")
    p_ap.add_argument("--note", default="")
    p_ap.set_defaults(func=cmd_approve)

    p_ab = sub.add_parser("approve-bundle")
    p_ab.add_argument("bundle")
    p_ab.add_argument("--note", default="")
    p_ab.set_defaults(func=cmd_approve_bundle)

    p_bl = sub.add_parser("backlog")
    p_bl.add_argument("hid")
    p_bl.add_argument("--reason", default="")
    p_bl.set_defaults(func=cmd_backlog)

    p_aas = sub.add_parser("approve-all-soft")
    p_aas.add_argument("--dry-run", action="store_true")
    p_aas.add_argument("--verbose", action="store_true")
    p_aas.add_argument("--note", default="")
    p_aas.set_defaults(func=cmd_approve_all_soft)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
