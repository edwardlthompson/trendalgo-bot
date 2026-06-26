import type { BacktestPayload } from "../api/client";
import { renderEquityChart } from "../charts/EquityChart";
import { createBacktestLibraryPanel, type LibraryRun } from "./library/BacktestLibrary";
import { t } from "../i18n";

export type BacktestPanelCallbacks = {
  onRun: () => void;
  onCloneRun?: (id: number) => void;
  onCompareRuns?: (ids: number[]) => void;
};

export function createBacktestPanel(
  payload: BacktestPayload | null,
  loading: boolean,
  callbacks: BacktestPanelCallbacks,
  libraryRuns: LibraryRun[] = [],
): { root: HTMLElement; cleanup: () => void } {
  const root = document.createElement("section");
  root.className = "gp-panel";
  root.dataset.testid = "backtest-panel";

  const header = document.createElement("div");
  header.className = "gp-panel-header";
  header.innerHTML = `<h2 class="gp-panel-title">${t("backtest.title")}</h2>`;
  const runBtn = document.createElement("button");
  runBtn.type = "button";
  runBtn.className = "gp-btn-primary";
  runBtn.textContent = loading ? t("backtest.running") : t("backtest.run");
  runBtn.disabled = loading;
  runBtn.dataset.testid = "backtest-run";
  runBtn.addEventListener("click", () => callbacks.onRun());
  header.appendChild(runBtn);
  root.appendChild(header);

  const toggles = document.createElement("div");
  toggles.className = "gp-backtest-toggles";
  toggles.dataset.testid = "backtest-toggles";
  toggles.innerHTML = `
    <label><input type="checkbox" data-slippage /> ${t("backtest.slippage")}</label>
    <label><input type="checkbox" data-fees /> ${t("backtest.fees")}</label>
  `;
  root.appendChild(toggles);

  root.appendChild(
    createBacktestLibraryPanel(
      libraryRuns,
      (id) => callbacks.onCloneRun?.(id),
      (ids) => callbacks.onCompareRuns?.(ids),
    ),
  );

  let cleanupChart = (): void => {};

  if (payload?.result) {
    const m = payload.metrics ?? {};
    const stats = document.createElement("dl");
    stats.className = "gp-stat-grid";
    stats.dataset.testid = "backtest-metrics";
    stats.innerHTML = `
      <div><dt>${t("metrics.profit")}</dt><dd>$${payload.result.profit_total.toFixed(2)}</dd></div>
      <div><dt>${t("metrics.sharpe")}</dt><dd>${(m.sharpe_ratio ?? 0).toFixed(2)}</dd></div>
      <div><dt>${t("metrics.sortino")}</dt><dd>${(m.sortino_ratio ?? 0).toFixed(2)}</dd></div>
      <div><dt>${t("metrics.calmar")}</dt><dd>${(m.calmar_ratio ?? 0).toFixed(2)}</dd></div>
      <div><dt>${t("metrics.win_rate")}</dt><dd>${(((m.win_rate ?? 0) as number) * 100).toFixed(0)}%</dd></div>
      <div><dt>${t("metrics.max_dd")}</dt><dd>${(((m.max_drawdown ?? 0) as number) * 100).toFixed(1)}%</dd></div>
    `;
    root.appendChild(stats);

    const chartHost = document.createElement("div");
    chartHost.className = "gp-chart-host";
    chartHost.dataset.testid = "equity-chart";
    root.appendChild(chartHost);
    cleanupChart = renderEquityChart(chartHost, payload.equity_curve);

    const timeline = document.createElement("ul");
    timeline.className = "gp-trade-timeline";
    timeline.dataset.testid = "trade-timeline";
    for (const trade of payload.result.trades) {
      const li = document.createElement("li");
      const pnl = Number(trade.profit_abs ?? 0);
      li.textContent = `${String(trade.pair)} · ${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}`;
      timeline.appendChild(li);
    }
    root.appendChild(timeline);

    if (payload.attribution) {
      const attr = document.createElement("dl");
      attr.className = "gp-stat-grid";
      attr.dataset.testid = "backtest-attribution";
      const a = payload.attribution;
      attr.innerHTML = `
        <div><dt>LTS</dt><dd>$${Number(a.lts_contribution_usd ?? 0).toFixed(2)}</dd></div>
        <div><dt>Scanner</dt><dd>$${Number(a.scanner_contribution_usd ?? 0).toFixed(2)}</dd></div>
      `;
      root.appendChild(attr);
    }
  } else {
    const empty = document.createElement("p");
    empty.className = "gp-body";
    empty.textContent = t("backtest.empty");
    root.appendChild(empty);
  }

  return {
    root,
    cleanup: () => cleanupChart(),
  };
}
