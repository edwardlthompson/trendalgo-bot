"""Product update rules: launch/daily window, asset parse, donate nudge, changelog."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.about.github_release import GithubRelease
from trendalgo.device.about.product_update import (
    MS_DAY,
    NamedAsset,
    is_newer_version,
    parse_asset_version,
    preview_release_notes,
    select_product_asset,
    should_check_daily,
    should_nudge_donate,
    should_prompt_update,
)
from trendalgo.device.about.run_updates import check_for_update, decide_launch_prompt
from trendalgo.device.about.update_prefs import mark_update_checked, mark_version_seen


def test_should_check_daily() -> None:
    assert should_check_daily(None, 1000) is True
    assert should_check_daily(1000, 1000 + MS_DAY) is True
    assert should_check_daily(1000, 1000 + MS_DAY - 1) is False


def test_is_newer_version() -> None:
    assert is_newer_version("0.6.0", "0.6.2") is True
    assert is_newer_version("0.6.2", "0.6.2") is False


def test_parse_and_select_exe_asset() -> None:
    assert parse_asset_version("TrendAlgo-0.7.0-x64-setup.exe", kind="exe", prefix="TrendAlgo") == (
        "0.7.0"
    )
    picked = select_product_asset(
        [NamedAsset("TrendAlgo-0.7.0-x64-setup.exe", "https://example/a.exe")],
        kind="exe",
        prefix="TrendAlgo",
    )
    assert picked == ("0.7.0", "https://example/a.exe")


def test_should_nudge_donate_and_prompt_update() -> None:
    assert should_nudge_donate(None, "0.6.2") is False
    assert should_nudge_donate("0.6.0", "0.6.2") is True
    assert should_prompt_update("0.6.0", "0.7.0", None) is True
    assert should_prompt_update("0.6.0", "0.7.0", "0.7.0") is False


def test_preview_release_notes_truncates() -> None:
    body = "## Notes\n\n" + ("word " * 300)
    preview = preview_release_notes(body, limit=80)
    assert preview.endswith("…")
    assert len(preview) <= 80
    assert "Notes" in preview
    assert "**bold**" not in preview_release_notes("**bold** item")


def test_decide_launch_prompt_donate_then_update(tmp_path: Path) -> None:
    mark_version_seen(tmp_path, "0.6.0")
    assert decide_launch_prompt(tmp_path, current_version="0.6.2").kind == "donate"  # type: ignore[union-attr]

    def fetch(_ver: str, _repo: str) -> GithubRelease:
        return GithubRelease(
            "https://github.com/acme/app/releases/tag/v0.7.0",
            (NamedAsset("TrendAlgo-0.7.0-x64-setup.exe", "https://example/a.exe"),),
            body="## What's new\n\n- Faster scans",
        )

    mark_version_seen(tmp_path, "0.6.2")
    prompt = decide_launch_prompt(
        tmp_path,
        current_version="0.6.2",
        now=MS_DAY * 2,
        release_repo="acme/app",
        fetch_latest=fetch,
        interval="launch",
    )
    assert prompt is not None
    assert prompt.kind == "update"
    assert prompt.version == "0.7.0"
    assert "Faster scans" in prompt.changelog


def test_launch_interval_ignores_daily_window(tmp_path: Path) -> None:
    mark_version_seen(tmp_path, "0.6.2")
    mark_update_checked(tmp_path, 1000.0)

    def fetch(_ver: str, _repo: str) -> GithubRelease:
        return GithubRelease(
            "https://github.com/acme/app/releases/tag/v0.7.0",
            (NamedAsset("TrendAlgo-0.7.0-x64-setup.exe", "https://example/a.exe"),),
        )

    # Within the daily window — launch still checks.
    prompt = decide_launch_prompt(
        tmp_path,
        current_version="0.6.2",
        now=1000.0 + 60_000,
        release_repo="acme/app",
        fetch_latest=fetch,
        interval="launch",
    )
    assert prompt is not None
    assert prompt.version == "0.7.0"

    # daily interval still respects the window.
    assert (
        decide_launch_prompt(
            tmp_path,
            current_version="0.6.2",
            now=1000.0 + 60_000,
            release_repo="acme/app",
            fetch_latest=fetch,
            interval="daily",
        )
        is None
    )


def test_force_check_ignores_dismissed(tmp_path: Path) -> None:
    mark_version_seen(tmp_path, "0.6.2")
    mark_update_checked(tmp_path, 1000.0, dismissed_version="0.7.0")

    def fetch(_ver: str, _repo: str) -> GithubRelease:
        return GithubRelease(
            "https://github.com/acme/app/releases/tag/v0.7.0",
            (NamedAsset("TrendAlgo-0.7.0-x64-setup.exe", "https://example/a.exe"),),
        )

    skipped = check_for_update(
        tmp_path,
        current_version="0.6.2",
        release_repo="acme/app",
        fetch_latest=fetch,
        force=False,
    )
    assert skipped.status == "current"

    forced = check_for_update(
        tmp_path,
        current_version="0.6.2",
        release_repo="acme/app",
        fetch_latest=fetch,
        force=True,
    )
    assert forced.status == "update"
    assert forced.prompt is not None
    assert forced.prompt.version == "0.7.0"


def test_settings_about_update_strings_present() -> None:
    from pathlib import Path

    body = Path("src/trendalgo/device/views/settings_page.py").read_text(encoding="utf-8")
    assert "AboutUpdatesSection" in body
    assert "settingsFormColumn" in body
    about = Path("src/trendalgo/device/views/about_updates_section.py").read_text(encoding="utf-8")
    assert "ABOUT_CHECK_UPDATES" in about
    assert "ABOUT_CHANGELOG" in about
