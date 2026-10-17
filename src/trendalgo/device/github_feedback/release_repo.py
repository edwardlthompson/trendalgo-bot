"""Load release_repo from .app-update.json (placeholder OWNER/REPO is ignored)."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.device.github_feedback.issue_form_url import is_placeholder_repo


def load_release_repo(search_roots: list[Path] | None = None) -> str:
    roots = search_roots if search_roots is not None else _default_roots()
    for root in roots:
        path = root / ".app-update.json"
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        repo = data.get("release_repo")
        if isinstance(repo, str) and not is_placeholder_repo(repo):
            return repo.strip()
    return ""


def _default_roots() -> list[Path]:
    roots = [Path.cwd()]
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file():
            roots.append(parent)
            break
    return roots
