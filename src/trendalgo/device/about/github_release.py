"""Fail-soft GitHub latest-release fetch for installer checks."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from trendalgo.device.about.product_update import NamedAsset
from trendalgo.device.github_feedback.issue_form_url import is_placeholder_repo


@dataclass(frozen=True)
class GithubRelease:
    html_url: str
    assets: tuple[NamedAsset, ...]
    body: str = ""


def release_page_url(repo: str) -> str:
    return f"https://github.com/{repo.strip()}/releases/latest"


def changelog_url(repo: str) -> str:
    cleaned = repo.strip()
    if not cleaned:
        return ""
    return f"https://github.com/{cleaned}/blob/main/CHANGELOG.md"


def fetch_latest_github_release(
    _current_version: str,
    release_repo: str,
    *,
    user_agent: str = "TrendAlgo/0",
) -> GithubRelease | None:
    if is_placeholder_repo(release_repo):
        return None
    url = f"https://api.github.com/repos/{release_repo.strip()}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": user_agent},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    html = data.get("html_url")
    html_url = html if isinstance(html, str) else release_page_url(release_repo)
    raw_body = data.get("body")
    body = raw_body if isinstance(raw_body, str) else ""
    assets: list[NamedAsset] = []
    for row in data.get("assets") or []:
        if not isinstance(row, dict):
            continue
        name, browser = row.get("name"), row.get("browser_download_url")
        if isinstance(name, str) and isinstance(browser, str):
            assets.append(NamedAsset(name, browser))
    return GithubRelease(html_url, tuple(assets), body)
