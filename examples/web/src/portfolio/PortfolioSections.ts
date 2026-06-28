import { t } from "../i18n";
import { formatUsd, formatPct } from "./formatUsd";
import type { GoalType } from "./GoalsPanel";

export type ComparisonRow = {
  label: string;
  title: string;
  pnl_usd: number;
  pnl_pct: number;
};

export type PortfolioOverviewData = {
  net_worth_usd: number;
  daily_pnl_usd: number;
  daily_pnl_pct: number;
  health_score: number;
  max_drawdown_pct: number;
  holdings: Array<Record<string, number | string>>;
  allocation: Array<{ asset: string; value_usd: number; pct: number }>;
  pl_breakdown: { realized_usd: number; unrealized_usd: number; total_usd: number };
  periods: Array<{ label: string; pnl_usd: number; pnl_pct: number }>;
  comparisons?: ComparisonRow[];
  accounts?: Array<{
    account_id: number;
    exchange: string;
    label: string;
    account_type: string;
    total_usd: number;
    holdings_count: number;
  }>;
  performance_goal?: {
    label: string;
    target_net_worth_usd: number;
    progress_pct: number;
    remaining_usd: number;
    current_net_worth_usd: number;
    goal_type?: GoalType;
    horizon_months?: number;
    target_return_pct?: number;
  };
  bot: Record<string, unknown>;
};

export type PortfolioCallbacks = {
  onSync: () => void;
  onSelectDate: (date: string) => void;
  onOpenInbox: () => void;
};

function statCell(label: string, value: string, testId?: string): string {
  const attr = testId ? ` data-testid="${testId}"` : "";
  return `<div><dt>${label}</dt><dd${attr}>${value}</dd></div>`;
}

export function createPortfolioHero(data: PortfolioOverviewData): HTMLElement {
  const hero = document.createElement("section");
  hero.className = "gp-portfolio-hero";
  hero.dataset.testid = "portfolio-hero";
  const pctSign = data.daily_pnl_pct >= 0 ? "+" : "";
  const comparisonCells = (data.comparisons ?? [])
    .map((row) =>
      statCell(
        row.title,
        `${formatUsd(row.pnl_usd, { signed: true })} (${formatPct(row.pnl_pct, { signed: true })})`,
        `overview-${row.label}`,
      ),
    )
    .join("");
  hero.innerHTML = `
    <h2 class="gp-panel-title">${t("portfolio.title")}</h2>
    <p class="gp-net-worth" data-testid="net-worth">${formatUsd(data.net_worth_usd)}</p>
    <p class="gp-daily-pl" data-testid="daily-pl">
      <span class="gp-pl-period">${t("portfolio.pl_period")}</span>
      ${formatUsd(data.daily_pnl_usd, { signed: true })}
      (${pctSign}${(data.daily_pnl_pct * 100).toFixed(2)}%)
    </p>
    <dl class="gp-overview-stats">
      ${statCell(t("portfolio.realized"), formatUsd(data.pl_breakdown.realized_usd, { signed: true }), "overview-realized")}
      ${statCell(t("portfolio.unrealized"), formatUsd(data.pl_breakdown.unrealized_usd, { signed: true }), "overview-unrealized")}
      ${statCell(t("portfolio.total_pl"), formatUsd(data.pl_breakdown.total_usd, { signed: true }), "overview-total-pl")}
      ${statCell(t("portfolio.health"), `${data.health_score}/100`)}
      ${statCell(t("health.drawdown"), `${(data.max_drawdown_pct * 100).toFixed(1)}%`)}
      ${comparisonCells}
    </dl>
  `;
  return hero;
}

export function createQuickActions(callbacks: PortfolioCallbacks): HTMLElement {
  const actions = document.createElement("div");
  actions.className = "gp-panel-actions";
  const syncBtn = document.createElement("button");
  syncBtn.type = "button";
  syncBtn.className = "gp-btn-primary";
  syncBtn.dataset.testid = "portfolio-sync";
  syncBtn.textContent = t("portfolio.refresh");
  syncBtn.addEventListener("click", () => callbacks.onSync());
  const inboxBtn = document.createElement("button");
  inboxBtn.type = "button";
  inboxBtn.className = "gp-btn-secondary";
  inboxBtn.dataset.testid = "open-inbox";
  inboxBtn.textContent = t("portfolio.inbox");
  inboxBtn.addEventListener("click", () => callbacks.onOpenInbox());
  actions.append(syncBtn, inboxBtn);
  return actions;
}

export function createBotUnifiedSection(bot: Record<string, unknown>): HTMLElement {
  const section = document.createElement("div");
  section.className = "gp-panel";
  section.dataset.testid = "bot-unified";
  section.innerHTML = `
    <h3>${t("portfolio.bot_section")}</h3>
    <dl class="gp-stat-grid">
      <div><dt>${t("dashboard.strategy")}</dt><dd>${bot.strategy_id}</dd></div>
      <div><dt>${t("dashboard.pair")}</dt><dd>${bot.pair}</dd></div>
      <div><dt>${t("dashboard.equity")}</dt><dd>${formatUsd(Number(bot.equity_usd ?? 0))}</dd></div>
      <div><dt>${t("dashboard.open_trades")}</dt><dd>${Array.isArray(bot.open_trades) ? bot.open_trades.length : 0}</dd></div>
    </dl>
  `;
  return section;
}
