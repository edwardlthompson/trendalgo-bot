"""Map BUILD_PLAN task text to sprint-smoke probe names."""

from __future__ import annotations

import re
from collections.abc import Iterable

from sprint_smoke_parse import SmokeItem

WORDS: dict[str, tuple[str, ...]] = {
    "web": (
        "web",
        "chrome",
        "lighthouse",
        "snapshot",
        "locale",
        "i18n",
        "vite",
        "playwright",
        "tokeniz",
        "empty state",
        "in-panel",
    ),
    "android": (
        "android",
        "compose",
        "talkback",
        "r8",
        "fdroid",
        "apk",
        "gradle",
        "unifiedpush",
        "rtl",
        "instrumented",
        "nav-stack",
        "runtime-budget",
    ),
    "node": ("node", "openapi spec", "hono"),
    "python": ("python", "mypy", "--feedback"),
    "rust": ("rust", "cargo.toml"),
    "go": (" go", "golang", "/module"),
    "lightroom": ("lightroom", "lua", "lr*"),
    "blender": ("blender", "cycles", "optix", "icon-factory"),
    "docs": (
        "docs/",
        "module.md",
        "catalog",
        "adr",
        "tour",
        "coach",
        "skill",
        "runbook",
        "winget",
        "dependabot",
        "scorecard",
        "semgrep",
        "nix",
        "radar",
        "ci-gap",
        "grok",
        "cursor",
        "automations",
        "canvas",
        "template-gap",
        "fastlane",
        "antifeatures",
        "signing",
        "glitchtip",
        "sanitizer",
        "automerge",
    ),
}

_BACKTICK = re.compile(r"`([^`]+)`")
_HTTP_VERBS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})
_SCOPE_MARK = "— scope:"
# "Delete" in a row means its `— scope:` paths are removed. "Delete" or "Removed" opens a clause
# whose backticked paths are removed too; the clause ends at the next sentence (". Capital").
_DELETE_WORD = re.compile(r"\bDelete\b")
_REMOVAL_CLAUSE = re.compile(r"\b(?:Delete|Removed)\b(.*?)(?=\.\s+[A-Z]|$)", re.S)


def infer_probes(task: str) -> list[str]:
    lower = f" {task.lower()} "
    found: list[str] = []
    for name, needles in WORDS.items():
        if any(n in lower for n in needles):
            found.append(name)
    if "openapi" in lower and "python" in lower and "node" not in found:
        found.append("python")
    if "openapi" in lower and "node" in lower and "node" not in found:
        found.append("node")
    if not found:
        found.append("docs")
    # Preserve order, unique
    return list(dict.fromkeys(found))


def probes_for_items(items: Iterable[SmokeItem]) -> dict[str, list[str]]:
    return {f"{item.number}:{item.task}": infer_probes(item.task) for item in items}


def _is_slash_command(text: str) -> bool:
    token = text.split()[0] if text else ""
    return token.startswith("/") and token.count("/") == 1 and "." not in token


def _repo_path(raw: str, task: str) -> str | None:
    """Return the repo path a backticked span names, or None when it names something else."""
    text = raw.strip()
    token = text.split()[0] if text else ""
    if not token or _is_slash_command(token):
        return None
    # HTTP routes (`GET /api/v1/status`) name a route, not a file.
    if token.upper() in _HTTP_VERBS:
        return None
    # URLs, `<placeholders>`, and `<!-- html comments -->` are templates; `*` is a glob.
    if "://" in token or any(ch in token for ch in "<>*"):
        return None
    # Host paths are not repo docs probes (e.g. `~/.local/bin`, absolute SDK trees).
    if token.startswith("~") or token.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", token):
        return None
    # "no `foo`" / "without `foo`" means absence is the requirement.
    if re.search(rf"\b(?:no|without|forbid(?:den)?)\s+`{re.escape(raw)}`", task, re.I):
        return None
    if "/" in text or token.endswith((".md", ".json", ".yml", ".yaml", ".html")):
        return token
    return None


def split_task_paths(task: str) -> tuple[list[str], list[str]]:
    """Split a row's backticked repo paths into (must exist, must be absent)."""
    body, mark, scope = task.partition(_SCOPE_MARK)
    if not mark:
        scope = ""
    removal_row = _DELETE_WORD.search(body) is not None
    removed_spans = [m.span(1) for m in _REMOVAL_CLAUSE.finditer(body)]
    present: list[str] = []
    gone: list[str] = []
    for m in _BACKTICK.finditer(body):
        path = _repo_path(m.group(1), task)
        if path is None:
            continue
        in_clause = any(lo <= m.start() < hi for lo, hi in removed_spans)
        (gone if in_clause else present).append(path)
    for m in _BACKTICK.finditer(scope):
        path = _repo_path(m.group(1), task)
        if path is not None:
            (gone if removal_row else present).append(path)
    return list(dict.fromkeys(present)), list(dict.fromkeys(gone))


def backtick_paths(task: str) -> list[str]:
    """Repo paths a row says must exist; removed paths come from split_task_paths."""
    return split_task_paths(task)[0]
