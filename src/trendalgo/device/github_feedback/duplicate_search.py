"""Fail-soft GitHub issue search for duplicate crash titles."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from trendalgo.device.github_feedback.cooldown import Cooldown
from trendalgo.device.github_feedback.issue_form_url import is_placeholder_repo

Fetch = Callable[[str, dict[str, str]], Any]


@dataclass(frozen=True)
class DuplicateIssue:
    title: str
    url: str
    number: int


_shared = Cooldown[list[DuplicateIssue]]()


def search_duplicate_issues(
    repo: str,
    fingerprint: str,
    *,
    fetch_impl: Fetch | None = None,
    user_agent: str = "TrendAlgo/0",
    cooldown: Cooldown[list[DuplicateIssue]] | None = None,
) -> list[DuplicateIssue]:
    cd = cooldown if cooldown is not None else _shared
    cached = cd.peek_search()
    if cached is not None:
        return cached
    if is_placeholder_repo(repo) or not fingerprint.strip():
        return []
    query = urlencode({"q": f'repo:{repo.strip()} "[crash] {fingerprint.strip()}" in:title'})
    api = f"https://api.github.com/search/issues?{query}"
    do_fetch = fetch_impl or _default_fetch
    try:
        payload = do_fetch(api, {"Accept": "application/vnd.github+json", "User-Agent": user_agent})
        items = payload.get("items") if isinstance(payload, dict) else None
        return cd.cached_search(parse_search_items(items))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError, ValueError):
        return cd.cached_search([])


def parse_search_items(items: object) -> list[DuplicateIssue]:
    if not isinstance(items, list):
        return []
    out: list[DuplicateIssue] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        url = item.get("html_url")
        number = item.get("number")
        if not isinstance(title, str) or not isinstance(url, str) or not isinstance(number, int):
            continue
        out.append(DuplicateIssue(title=title, url=url, number=number))
    return out


def _default_fetch(url: str, headers: dict[str, str]) -> Any:
    if not url.startswith("https://"):
        return {"items": []}
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))
