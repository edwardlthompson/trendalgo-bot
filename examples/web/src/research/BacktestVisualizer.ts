import type { BacktestPayload } from "../api/client";
import { t } from "../i18n";

export function createBacktestVisualizer(payload: BacktestPayload | null): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "backtest-visualizer";
  section.innerHTML = `<h3>${t("research.visualizer")}</h3>`;
  if (!payload?.result) {
    section.innerHTML += `<p>${t("backtest.empty")}</p>`;
    return section;
  }
  const dd = payload.result.max_drawdown ?? 0;
  const timeline = document.createElement("ul");
  timeline.className = "gp-trade-timeline-detailed";
  for (const trade of payload.result.trades) {
    const li = document.createElement("li");
    const pnl = Number(trade.profit_abs ?? 0);
    li.textContent = `${String(trade.pair)} · P/L $${pnl.toFixed(2)}`;
    timeline.appendChild(li);
  }
  section.innerHTML += `<p>Max DD: ${(Number(dd) * 100).toFixed(1)}%</p>`;
  section.appendChild(timeline);
  if (payload.analysis?.disclaimer) {
    const disc = document.createElement("p");
    disc.className = "gp-disclaimer";
    disc.textContent = String(payload.analysis.disclaimer);
    section.appendChild(disc);
  }
  return section;
}
