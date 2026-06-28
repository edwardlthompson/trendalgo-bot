import { renderBotChart, type BotChartData, type BotTradeMarker } from "../charts/BotChart";
import type { EquityPoint } from "../charts/EquityChart";
import { t } from "../i18n";

export type BotChartTabInput = {
  chart: EquityPoint[];
  ohlcv?: BotChartData["ohlcv"];
  actualMarkers: BotTradeMarker[];
  simulatedMarkers: BotTradeMarker[];
  tradeRegions?: BotChartData["regions"];
  simulatedRegions?: BotChartData["regions"];
};

export function createBotChartTabs(input: BotChartTabInput): { root: HTMLElement; cleanup: () => void } {
  const root = document.createElement("div");
  root.className = "gp-bot-chart-tabs";
  root.dataset.testid = "bot-chart-tabs";

  const tabs = document.createElement("div");
  tabs.className = "gp-tab-row";
  tabs.innerHTML = `
    <button type="button" class="gp-tab gp-tab-active" data-tab="actual">${t("bots.detail.chart_actual")}</button>
    <button type="button" class="gp-tab" data-tab="simulated">${t("bots.detail.chart_simulated")}</button>
  `;

  const host = document.createElement("div");
  host.className = "gp-bot-detail-chart";
  host.dataset.testid = "bot-detail-chart";

  let mode: "actual" | "simulated" = "actual";
  const pack = (m: "actual" | "simulated"): BotChartData => ({
    points: input.chart,
    ohlcv: input.ohlcv,
    trades: m === "actual" ? input.actualMarkers : input.simulatedMarkers,
    regions: m === "actual" ? input.tradeRegions : input.simulatedRegions,
  });

  const handle = renderBotChart(host, pack("actual"));

  tabs.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest("[data-tab]") as HTMLElement | null;
    if (!btn) return;
    mode = btn.dataset.tab === "simulated" ? "simulated" : "actual";
    for (const tab of tabs.querySelectorAll(".gp-tab")) tab.classList.remove("gp-tab-active");
    btn.classList.add("gp-tab-active");
    handle.setData(pack(mode));
  });

  root.append(tabs, host);
  return { root, cleanup: () => handle.cleanup() };
}
