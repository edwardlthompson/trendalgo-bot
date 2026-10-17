"""Settings Dashboard modules min-size editor."""

from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot

from trendalgo.device.context import open_context
from trendalgo.device.portfolio_layout_prefs import load_prefs
from trendalgo.device.portfolio_module_catalog import spec_for
from trendalgo.device.views.collapsible_section import CollapsibleSection
from trendalgo.device.views.dashboard_modules_settings import DashboardModulesSection


def test_collapsible_section_toggles(qtbot: QtBot) -> None:
    section = CollapsibleSection("Demo", expanded=True)
    qtbot.addWidget(section)
    section.show()
    assert section._expanded is True
    assert section._chevron.text() == "▼"
    assert section._body.isVisibleTo(section)
    section._flip()
    assert section._expanded is False
    assert section._chevron.text() == "▶"
    assert not section._body.isVisibleTo(section)
    section.set_expanded(True)
    assert section._expanded is True


def test_dashboard_modules_section_save_override(qtbot: QtBot, tmp_path: Path) -> None:
    ctx = open_context(tmp_path / "profile")
    section = DashboardModulesSection(ctx)
    qtbot.addWidget(section)
    assert "total_worth" in section._spins
    w_spin, h_spin = section._spins["total_worth"]
    spec = spec_for("total_worth")
    assert spec is not None
    w_spin.setValue(min(spec.max_w, spec.min_w + 2))
    h_spin.setValue(min(spec.max_h, spec.min_h + 1))
    section.save()
    prefs = load_prefs(ctx.root)
    assert "total_worth" in prefs.module_mins
    assert prefs.module_mins["total_worth"][0] == w_spin.value()
    section._reset_defaults()
    prefs2 = load_prefs(ctx.root)
    assert "total_worth" not in prefs2.module_mins
