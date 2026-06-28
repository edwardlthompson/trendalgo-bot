import type { BotDetailData, BacktestRanking } from "../api/client";
import { formatUsd, formatPct } from "../portfolio/formatUsd";
import { t } from "../i18n";
import { createBacktestTop5Bar } from "./backtestTop5Bar";
import { createBotChartTabs } from "./botChartTabs";
import { createBotSettingsForm, type BotSettingsContext } from "./botSettingsForm";

export type BotUpdatePayload = {
  label: string;
  strategy_id: string;
  pair: string;
  exchange: string;
  equity_usd: number;
  equity_mode: "base" | "quote" | "portfolio_pct";
  equity_input: number;
  timeframe: string;
  ta_params: Record<string, number>;
};

export type BotDetailCallbacks = {
  settings: BotSettingsContext;
  onBack: () => void;
  onSave: (botId: number, payload: BotUpdatePayload) => void;
  onSaveParams: (botId: number, strategyId: string, params: Record<string, number>) => void;
  onApplyBacktest: (botId: number, ranking: BacktestRanking) => void;
  onSaveTemplate: (botId: number, name: string) => void;
};

function tradeTimeSec(iso: string): number {
  return Math.floor(new Date(iso).getTime() / 1000);
}

function markersFromTrades(
  trades: BotDetailData["trades"],
  preset?: BotDetailData["trade_markers"],
): import("../charts/BotChart").BotTradeMarker[] {
  if (preset?.length) {
    return preset.map((m) => ({
      time: Number(m.time),
      side: String(m.side),
      pnl_usd: m.pnl_usd != null ? Number(m.pnl_usd) : undefined,
      pnl_pct: m.pnl_pct != null ? Number(m.pnl_pct) : undefined,
    }));
  }
  let openStake = 0;
  const out: import("../charts/BotChart").BotTradeMarker[] = [];
  for (const trade of [...trades].sort((a, b) => tradeTimeSec(String(a.created_at)) - tradeTimeSec(String(b.created_at)))) {
    const side = String(trade.side).toLowerCase();
    const time = tradeTimeSec(String(trade.created_at));
    if (side === "buy") {
      openStake = Number(trade.stake_usd) || openStake;
      out.push({ time, side });
      continue;
    }
    if (side !== "sell") continue;
    const stake = Number(trade.stake_usd) || openStake;
    const pnl = Number(trade.pnl_usd);
    const pnlPct = stake > 0 ? (pnl / stake) * 100 : undefined;
    out.push({ time, side, pnl_usd: pnl, pnl_pct: pnlPct });
    openStake = 0;
  }
  return out;
}

export function createBotDetailPage(
  detail: BotDetailData,
  callbacks: BotDetailCallbacks,
  options?: { paperLocal?: boolean },
): { root: HTMLElement; cleanup: () => void } {
  const bot = detail.bot;
  const root = document.createElement("section");
  root.className = "gp-panel gp-bot-detail";
  root.dataset.testid = "bot-detail";

  const backBtn = document.createElement("button");
  backBtn.type = "button";
  backBtn.className = "gp-btn-secondary gp-bot-back";
  backBtn.dataset.testid = "bot-detail-back";
  backBtn.textContent = t("bots.detail.back");
  backBtn.addEventListener("click", () => callbacks.onBack());

  const header = document.createElement("div");
  header.className = "gp-bot-detail-header";
  header.innerHTML = `
    <h2 class="gp-panel-title">${bot.label}</h2>
    <span class="gp-bot-status ${bot.enabled ? "gp-bot-status-on" : "gp-bot-status-off"}">
      ${bot.enabled ? t("bots.status.running") : t("bots.status.stopped")}
    </span>
  `;
  header.prepend(backBtn);

  const paperNote =
    options?.paperLocal
      ? (() => {
          const note = document.createElement("p");
          note.className = "gp-bot-paper-note";
          note.dataset.testid = "bot-detail-paper-note";
          note.textContent = t("bots.detail.paper_mode");
          return note;
        })()
      : null;

  const summary = document.createElement("dl");
  summary.className = "gp-bot-detail-summary";
  summary.innerHTML = `
    <div><dt>${t("portfolio.realized")}</dt><dd>${formatUsd(detail.realized_pnl_usd, { signed: true })}</dd></div>
    <div><dt>${t("portfolio.unrealized")}</dt><dd>${formatUsd(detail.unrealized_pnl_usd, { signed: true })}</dd></div>
    <div><dt>${t("portfolio.total_pl")}</dt><dd data-testid="bot-detail-pnl">${formatUsd(detail.pnl_usd, { signed: true })} (${formatPct(detail.pnl_pct, { signed: true })})</dd></div>
    <div><dt>${t("bots.detail.trades")}</dt><dd>${detail.trade_count}</dd></div>
  `;

  const top5 = createBacktestTop5Bar(detail.backtest_top5 ?? [], (ranking) =>
    callbacks.onApplyBacktest(bot.id, ranking),
  );

  const settings = createBotSettingsForm(detail, callbacks.settings, (payload) =>
    callbacks.onSave(bot.id, payload),
  );

  const templateRow = document.createElement("div");
  templateRow.className = "gp-bot-save-template-row";
  templateRow.dataset.testid = "bot-save-template-row";
  const templateName = document.createElement("input");
  templateName.type = "text";
  templateName.className = "gp-bot-template-name";
  templateName.dataset.testid = "bot-template-name";
  templateName.placeholder = t("bots.templates.name_placeholder");
  templateName.value = `${bot.label} template`;
  const saveTplBtn = document.createElement("button");
  saveTplBtn.type = "button";
  saveTplBtn.className = "gp-btn-secondary";
  saveTplBtn.dataset.testid = "bot-save-template";
  saveTplBtn.textContent = t("bots.templates.save");
  saveTplBtn.addEventListener("click", () => {
    callbacks.onSaveTemplate(bot.id, templateName.value.trim() || bot.label);
  });
  templateRow.append(templateName, saveTplBtn);

  const paramsForm = document.createElement("form");
  paramsForm.className = "gp-bot-detail-params";
  paramsForm.dataset.testid = "bot-detail-params";
  paramsForm.innerHTML = `<h3 class="gp-panel-subtitle">${t("bots.detail.strategy_params")}</h3>`;
  const specs = detail.param_specs.length
    ? detail.param_specs
    : Object.keys(detail.strategy_params).map((key) => ({ key, label: key, default: detail.strategy_params[key] }));
  for (const spec of specs) {
    const key = String(spec.key);
    const val = detail.strategy_params[key] ?? spec.default ?? 0;
    const label = document.createElement("label");
    label.innerHTML = `${String(spec.label ?? key)}<input name="${key}" type="number" step="any" value="${val}" />`;
    paramsForm.appendChild(label);
  }
  const saveParamsBtn = document.createElement("button");
  saveParamsBtn.type = "submit";
  saveParamsBtn.className = "gp-btn-secondary";
  saveParamsBtn.textContent = t("bots.detail.save_params");
  paramsForm.appendChild(saveParamsBtn);

  const chartWrap = document.createElement("div");
  chartWrap.className = "gp-bot-detail-chart-wrap";
  chartWrap.innerHTML = `<h3 class="gp-panel-subtitle">${t("bots.detail.chart")}</h3>`;
  const chartTabs = createBotChartTabs({
    chart: detail.chart,
    ohlcv: detail.ohlcv,
    actualMarkers: markersFromTrades(detail.trades, detail.trade_markers),
    simulatedMarkers: markersFromTrades(detail.simulated_trades ?? [], detail.simulated_markers),
    tradeRegions: detail.trade_regions,
    simulatedRegions: detail.simulated_regions,
  });
  chartWrap.appendChild(chartTabs.root);

  const tradesTable = document.createElement("div");
  tradesTable.className = "gp-bot-trades-table";
  tradesTable.dataset.testid = "bot-detail-trades";
  if (!detail.trades.length) {
    tradesTable.innerHTML = `<p>${t("bots.detail.no_trades")}</p>`;
  } else {
    const rows = detail.trades
      .slice()
      .reverse()
      .map(
        (trade) =>
          `<tr><td>${String(trade.created_at).slice(0, 19)}</td><td>${trade.side}</td><td>${formatUsd(Number(trade.stake_usd))}</td><td>${formatUsd(Number(trade.pnl_usd), { signed: true })}</td></tr>`,
      )
      .join("");
    tradesTable.innerHTML = `
      <h3 class="gp-panel-subtitle">${t("bots.detail.trade_history")}</h3>
      <table class="gp-table"><thead><tr><th>${t("bots.detail.time")}</th><th>${t("bots.detail.side")}</th><th>${t("bots.detail.stake")}</th><th>${t("bots.detail.pnl")}</th></tr></thead><tbody>${rows}</tbody></table>
    `;
  }

  paramsForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const fd = new FormData(paramsForm);
    const params: Record<string, number> = {};
    for (const [key, value] of fd.entries()) {
      if (key === "submit") continue;
      params[key] = Number(value);
    }
    callbacks.onSaveParams(bot.id, bot.strategy_id, params);
  });

  root.append(
    header,
    ...(paperNote ? [paperNote] : []),
    summary,
    ...(top5 ? [top5] : []),
    settings.form,
    templateRow,
    paramsForm,
    chartWrap,
    tradesTable,
  );

  return {
    root,
    cleanup: () => {
      settings.cleanup();
      chartTabs.cleanup();
    },
  };
}
