"""Content lint for docker/Dockerfile.bot and its release manifest (row 15; W-OCI4; L6)."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCKERFILE = (REPO / "docker" / "Dockerfile.bot").read_text(encoding="utf-8")
FROM_LINES = [line for line in DOCKERFILE.splitlines() if line.startswith("FROM ")]


def test_the_base_image_is_pinned_to_a_tag_and_never_latest() -> None:
    assert len(FROM_LINES) == 1
    image = FROM_LINES[0].split()[1]
    assert ":" in image
    assert "latest" not in image


def test_the_container_runs_as_the_non_root_bot_user() -> None:
    assert "USER bot" in DOCKERFILE.splitlines()
    assert "USER root" not in DOCKERFILE
    assert "useradd" in DOCKERFILE


def test_the_container_serves_tls_on_8443_through_the_factory() -> None:
    assert "EXPOSE 8443" in DOCKERFILE
    assert "--factory" in DOCKERFILE
    assert "trendalgo.botd.service:build_app" in DOCKERFILE
    assert "/run/secrets/botd.key" in DOCKERFILE


def test_the_build_installs_only_the_locked_base_dependencies() -> None:
    assert "uv sync --frozen --no-dev" in DOCKERFILE
    assert "--extra" not in DOCKERFILE
    assert (REPO / "uv.lock").is_file()


def test_uv_is_pinned_to_the_version_the_project_uses() -> None:
    assert "uv==0.11.21" in DOCKERFILE


def test_the_host_image_has_no_talib_because_the_base_dependencies_omit_it() -> None:
    assert "talib" not in DOCKERFILE.lower()
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert not [dep for dep in project["dependencies"] if "ta-lib" in dep.lower()]


def test_the_release_manifest_refuses_every_install_until_it_is_pinned() -> None:
    manifest = json.loads((REPO / "docker" / "botd-release.json").read_text(encoding="utf-8"))
    assert manifest["image_sha256"] is None
