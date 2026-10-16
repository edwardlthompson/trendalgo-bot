"""Token guard: the device constants match design-tokens.json, the generated file is current,
and device UI code holds no raw hex colors (the design guide rule).
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

from trendalgo.device import design_tokens as T

ROOT = Path(__file__).resolve().parents[2]
TOKENS = ROOT / "design-tokens" / "design-tokens.json"
DEVICE_SRC = ROOT / "src" / "trendalgo" / "device"
SYNC = ROOT / "scripts" / "sync-design-tokens.py"
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")


def _tokens() -> dict:
    return json.loads(TOKENS.read_text(encoding="utf-8"))


def _sync_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sync_design_tokens", SYNC)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_device_colors_match_the_token_file() -> None:
    colors = _tokens()["color"]
    assert T.LIGHT == {key: value["light"] for key, value in colors.items()}
    assert T.DARK == {key: value["dark"] for key, value in colors.items()}


def test_device_spacing_radius_and_type_match_the_token_file() -> None:
    tokens = _tokens()
    assert T.SPACING == tokens["spacing"]
    assert T.RADIUS == tokens["radius"]
    scale = tokens["typography"]["scale"]
    assert T.TEXT_SIZE_SP == {key: value["sizeSp"] for key, value in scale.items()}


def test_accent_presets_match_the_token_file() -> None:
    assert list(T.ACCENT_PRESETS) == _tokens()["meta"]["accentPresets"]


def test_the_generated_device_module_is_current() -> None:
    sync = _sync_module()
    tokens = _tokens()
    digest = sync.token_hash(tokens)
    mark = (ROOT / "branding" / "assets" / "logo-mark.svg").read_text(encoding="utf-8")
    expected = sync.generate_device_module(tokens, digest, mark)
    actual = (DEVICE_SRC / "design_tokens.py").read_text(encoding="utf-8")
    assert actual == expected, "run scripts/sync-design-tokens.py to refresh design_tokens.py"


def test_the_brand_mark_is_the_logo_svg() -> None:
    mark = (ROOT / "branding" / "assets" / "logo-mark.svg").read_text(encoding="utf-8")
    assert T.BRAND_MARK_SVG.strip() == mark.strip()


def test_device_ui_code_has_no_raw_hex_colors() -> None:
    offenders = []
    for path in sorted(DEVICE_SRC.rglob("*.py")):
        if path.name == "design_tokens.py":
            continue
        if HEX.search(path.read_text(encoding="utf-8")):
            offenders.append(path.name)
    assert offenders == []
