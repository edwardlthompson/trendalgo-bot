"""Build https://github.com/.../issues/new URLs with clipboard fallback for large bodies."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

MAX_QUERY_CHARS = 1800


def is_placeholder_repo(repo: str) -> bool:
    trimmed = repo.strip()
    return not trimmed or trimmed.upper() == "OWNER/REPO"


def crash_title(fingerprint: str, exception_type: str) -> str:
    fp = "".join(ch for ch in fingerprint if ch in "0123456789abcdefABCDEF")[:12].lower()
    raw = exception_type or "Error"
    buf: list[str] = []
    for ch in raw:
        if ch.isalnum() or ch in "_.$":
            buf.append(ch)
        else:
            break
    return f"[crash] {fp} {''.join(buf) or 'Error'}"


def build_issue_form_url(
    repo: str,
    template: str,
    fields: dict[str, Any],
) -> dict[str, Any]:
    trimmed = repo.strip()
    if is_placeholder_repo(trimmed):
        return {"url": "", "body_too_large": False}
    base = f"https://github.com/{trimmed}/issues/new"
    params: dict[str, str] = {"template": template}
    title = fields.get("title")
    labels = fields.get("labels")
    if isinstance(title, str) and title:
        params["title"] = title
    if isinstance(labels, str) and labels:
        params["labels"] = labels
    for key, value in fields.items():
        if not value or key in {"title", "labels"}:
            continue
        if isinstance(value, str):
            params[key] = value
    full = f"{base}?{urlencode(params)}"
    if len(full) <= MAX_QUERY_CHARS:
        return {"url": full, "body_too_large": False}
    short: dict[str, str] = {"template": template}
    if isinstance(title, str) and title:
        short["title"] = title
    markdown = (
        fields.get("stack")
        or fields.get("description")
        or fields.get("reproduction")
        or fields.get("problem")
        or ""
    )
    return {
        "url": f"{base}?{urlencode(short)}",
        "clipboard_markdown": str(markdown) if markdown else None,
        "body_too_large": True,
    }
