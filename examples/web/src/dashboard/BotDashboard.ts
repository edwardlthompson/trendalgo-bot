import type { DashboardData } from "../api/client";
import { formatUsd, formatPct } from "../portfolio/formatUsd";
import { t } from "../i18n";
import type { BotLimits, BotLike } from "../bots/botGuardrails";
import { canEnableBot, isBotEnabled } from "../bots/botGuardrails";
import { formatGuardrailIssue } from "../bots/botLimitsBanner";
import type { BotTemplate } from "../bots/botTemplatesStore";
import { createBotDashboardToolbar } from "./botDashboardToolbar";

export type BotRecord = NonNullable<DashboardData["bots"]>[number];

export type BotUpdatePayload = {
  label: string;
  strategy_id: string;
  pair: string;
  equity_usd: number;
  timeframe: string;
};

export type BotDashboardCallbacks = {
  onOpenBot: (botId: number) => void;
  onToggleEnabled: (botId: number, enabled: boolean) => void;
  onDelete: (botId: number) => void;
  onForceTrade: (botId: number, side: "buy" | "sell") => void;
  onCreateBot: () => void;
  onApplyTemplate: (templateId: string) => void;
  onDeleteTemplate: (templateId: string) => void;
};

function iconButton(
  label: string,
  glyph: string,
  testId: string,
  onClick: () => void,
): HTMLButtonElement {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "gp-icon-btn";
  btn.dataset.testid = testId;
  btn.setAttribute("aria-label", label);
  btn.title = label;
  btn.textContent = glyph;
  btn.addEventListener("click", (event) => {
    event.stopPropagation();
    onClick();
  });
  return btn;
}

function plBlock(bot: BotRecord, testId: string): string {
  const realized = Number(bot.realized_pnl_usd ?? 0);
  const unrealized = Number(bot.unrealized_pnl_usd ?? 0);
  const total = Number(bot.pnl_usd ?? realized + unrealized);
  const pct = Number(bot.pnl_pct ?? 0);
  return `
    <div class="gp-bot-pl-block" data-testid="${testId}">
      <div><dt>${t("portfolio.realized")}</dt><dd>${formatUsd(realized, { signed: true })}</dd></div>
      <div><dt>${t("portfolio.unrealized")}</dt><dd>${formatUsd(unrealized, { signed: true })}</dd></div>
      <div><dt>${t("portfolio.total_pl")}</dt><dd>${formatUsd(total, { signed: true })} (${formatPct(pct, { signed: true })})</dd></div>
    </div>
  `;
}

function createBotCard(bot: BotRecord, callbacks: BotDashboardCallbacks, limits?: BotLimits, bots?: BotLike[]): HTMLElement {
  const card = document.createElement("article");
  card.className = "gp-bot-card";
  card.dataset.testid = `bot-card-${bot.id}`;

  const header = document.createElement("div");
  header.className = "gp-bot-card-header";
  const title = document.createElement("button");
  title.type = "button";
  title.className = "gp-bot-card-title gp-bot-card-link";
  title.dataset.testid = `bot-open-${bot.id}`;
  title.textContent = bot.label;
  title.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    callbacks.onOpenBot(bot.id);
  });
  const status = document.createElement("span");
  status.className = isBotEnabled(bot.enabled) ? "gp-bot-status gp-bot-status-on" : "gp-bot-status gp-bot-status-off";
  status.textContent = isBotEnabled(bot.enabled) ? t("bots.status.running") : t("bots.status.stopped");
  header.append(title, status);

  const meta = document.createElement("dl");
  meta.className = "gp-bot-card-meta";
  meta.innerHTML = `
    <div><dt>${t("dashboard.strategy")}</dt><dd>${bot.strategy_id}</dd></div>
    <div><dt>${t("dashboard.pair")}</dt><dd>${bot.pair}</dd></div>
    <div><dt>${t("bots.field.timeframe")}</dt><dd>${bot.timeframe ?? "1h"}</dd></div>
    <div><dt>${t("dashboard.equity")}</dt><dd>${formatUsd(bot.equity_usd)}</dd></div>
    ${plBlock(bot, `bot-pnl-${bot.id}`)}
    <div><dt>${t("dashboard.engine")}</dt><dd>${bot.engine ?? "native"} · ${bot.exchange ?? "kraken"}</dd></div>
  `;

  const actions = document.createElement("div");
  actions.className = "gp-bot-card-actions";
  if (isBotEnabled(bot.enabled)) {
    actions.append(
      iconButton(t("bots.action.pause"), "⏸", `bot-pause-${bot.id}`, () =>
        callbacks.onToggleEnabled(bot.id, false),
      ),
    );
  } else {
    const enableBlock = limits && bots ? canEnableBot(limits, bots, bot) : null;
    const playBtn = iconButton(
      enableBlock ? formatGuardrailIssue(enableBlock) : t("bots.action.play"),
      "▶",
      `bot-play-${bot.id}`,
      () => callbacks.onToggleEnabled(bot.id, true),
    );
    if (enableBlock) {
      playBtn.disabled = true;
      playBtn.title = formatGuardrailIssue(enableBlock);
      playBtn.dataset.testid = `bot-play-blocked-${bot.id}`;
    }
    actions.append(playBtn);
  }
  actions.append(
    iconButton(t("bots.action.delete"), "✕", `bot-delete-${bot.id}`, () => {
      if (window.confirm(t("bots.confirm_delete"))) callbacks.onDelete(bot.id);
    }),
  );

  const tradeRow = document.createElement("div");
  tradeRow.className = "gp-bot-trade-actions";
  const buyBtn = document.createElement("button");
  buyBtn.type = "button";
  buyBtn.className = "gp-btn-secondary gp-bot-force-btn";
  buyBtn.dataset.testid = `bot-buy-${bot.id}`;
  buyBtn.textContent = t("bots.action.buy_now");
  buyBtn.addEventListener("click", () => callbacks.onForceTrade(bot.id, "buy"));
  const sellBtn = document.createElement("button");
  sellBtn.type = "button";
  sellBtn.className = "gp-btn-secondary gp-bot-force-btn";
  sellBtn.dataset.testid = `bot-sell-${bot.id}`;
  sellBtn.textContent = t("bots.action.sell_now");
  sellBtn.addEventListener("click", () => callbacks.onForceTrade(bot.id, "sell"));
  tradeRow.append(buyBtn, sellBtn);

  card.append(header, meta, actions, tradeRow);
  return card;
}

export function createBotDashboard(
  data: DashboardData,
  callbacks: BotDashboardCallbacks,
  extras?: { templates: BotTemplate[]; limits: BotLimits },
): HTMLElement {
  const limits = extras?.limits;
  const bots = data.bots ?? [];
  const section = document.createElement("section");
  section.className = "gp-panel gp-bot-dashboard";
  section.dataset.testid = "bot-dashboard";

  const header = document.createElement("div");
  header.className = "gp-bot-dashboard-header";
  header.innerHTML = `
    <h2 class="gp-panel-title">${t("dashboard.title")}</h2>
    <span class="gp-badge ${data.dry_run ? "gp-badge-dry" : "gp-badge-live"}">
      ${data.dry_run ? t("health.dry_run") : t("health.live")}
    </span>
  `;
  section.appendChild(header);

  if (extras) {
    section.appendChild(
      createBotDashboardToolbar(extras.templates, extras.limits, bots, {
        onCreateBot: callbacks.onCreateBot,
        onApplyTemplate: callbacks.onApplyTemplate,
        onDeleteTemplate: callbacks.onDeleteTemplate,
      }),
    );
  }

  const grid = document.createElement("div");
  grid.className = "gp-bot-card-grid";
  grid.dataset.testid = "bot-card-grid";
  if (!bots.length) {
    grid.innerHTML = `<p>${t("bots.empty")}</p>`;
  } else {
    for (const bot of bots) {
      grid.appendChild(createBotCard(bot, callbacks, limits, bots));
    }
  }
  section.appendChild(grid);
  return section;
}

export function createBotDetailLoading(_label: string): HTMLElement {
  const panel = document.createElement("section");
  panel.className = "gp-panel gp-bot-detail-loading";
  panel.dataset.testid = "bot-detail-loading";
  panel.innerHTML = `<p class="gp-body">${t("bots.detail.loading")}</p>`;
  return panel;
}
