"""Copy FOSS MCP example → gitignored .cursor/mcp.json and report leftover human steps."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _preferred_example(root: Path) -> Path:
    web = root / ".cursor" / "mcp.web.example"
    foss = root / ".cursor" / "mcp.foss.example"
    if web.is_file():
        return web
    return foss


def _windows_npx() -> str | None:
    if os.name != "nt":
        return None
    candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs" / "npx.cmd"
    return str(candidate) if candidate.is_file() else None


def _rewrite_npx_commands(data: dict) -> bool:
    """On Windows, replace bare `npx` with absolute npx.cmd when Node is installed."""
    npx = _windows_npx()
    if not npx:
        return False
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        return False
    changed = False
    for cfg in servers.values():
        if not isinstance(cfg, dict):
            continue
        cmd = str(cfg.get("command") or "")
        if cmd in ("npx", "npx.cmd") or cmd.endswith("\\npx") or cmd.endswith("/npx"):
            cfg["command"] = npx
            changed = True
    return changed


def activate(root: Path, *, force: bool = False) -> int:
    src = _preferred_example(root)
    if not src.is_file():
        print(f"FAIL: missing {src.relative_to(root).as_posix()}", file=sys.stderr)
        return 1
    dst = root / ".cursor" / "mcp.json"
    wrote = False
    if force or not dst.is_file():
        shutil.copyfile(src, dst)
        wrote = True
        print(f"OK   wrote {dst.relative_to(root).as_posix()} from {src.name}")
    else:
        print(f"OK   {dst.relative_to(root).as_posix()} already present (use --force to refresh)")

    try:
        data = json.loads(dst.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot parse mcp.json: {exc}", file=sys.stderr)
        return 1
    if _rewrite_npx_commands(data):
        dst.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print("OK   rewritten MCP commands to absolute Windows npx.cmd (Node not on PATH)")
        wrote = True
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    if not isinstance(servers, dict) or not servers:
        print("FAIL: mcp.json has no mcpServers", file=sys.stderr)
        return 1
    print(f"OK   MCP servers: {', '.join(sorted(servers))}")

    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    leftovers: list[str] = []
    if "github" in servers and not token:
        leftovers.append(
            "Set User env var GITHUB_TOKEN (classic PAT with repo scope), "
            "or ensure `gh auth token` works, then re-open Cursor."
        )
    else:
        print("OK   GITHUB_TOKEN/GH_TOKEN present in this shell (or github MCP unused)")

    leftovers.append("Restart Cursor (or Reload Window) so MCP servers load.")
    if wrote:
        leftovers.append("Confirm Tools/MCP shows github + depsonar (no red errors).")

    print()
    print("HUMAN leftovers (script cannot finish these):")
    for i, step in enumerate(leftovers, 1):
        print(f"  {i}. {step}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--force", action="store_true", help="Overwrite existing mcp.json")
    args = p.parse_args(argv)
    return activate(args.root.resolve(), force=args.force)


if __name__ == "__main__":
    raise SystemExit(main())
