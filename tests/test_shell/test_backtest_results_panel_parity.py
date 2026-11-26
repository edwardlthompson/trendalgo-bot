"""Parity checks for POL7-01: Backtest tab matches single-coin Results surface."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHELL = ROOT / "shell" / "TrendAlgo.Shell"


def test_backtest_tab_hosts_results_panel_and_not_workbook() -> None:
    catalog = (SHELL / "Models" / "ParityCatalog.cs").read_text(encoding="utf-8")
    assert '"workbook" or "crypto" or "tradfi" or "forex" or "sauce"' in catalog

    main_axaml = (SHELL / "Views" / "MainWindow.axaml").read_text(encoding="utf-8")
    assert '<controls:BacktestResultsPanel IsVisible="{Binding ShowBacktestStrip}" />' in main_axaml
    assert "MarketContextText" not in main_axaml


def test_backtest_results_panel_matches_results_surface_structure() -> None:
    panel = (SHELL / "Controls" / "BacktestResultsPanel.axaml").read_text(encoding="utf-8")
    for kind in ('Kind="signal"', 'Kind="levels"', 'Kind="risk"', 'Kind="structure"'):
        assert kind in panel
    assert "BacktestColumnFilterBar" in panel
    assert "HeatValueCell" in panel
    assert 'Content="Create Bot"' in panel


def test_backtest_vm_clones_market_context_and_hides_workbook() -> None:
    vm = (SHELL / "ViewModels" / "MainViewModel.Backtest.cs").read_text(encoding="utf-8")
    assert "mc.Clone()" in vm
    assert "ShowWorkbook = false;" in vm
    assert "BacktestCreateBotForResultRow" in vm
    assert "BacktestOpenChart7d" in vm
    assert "BacktestOpenChart30d" in vm
