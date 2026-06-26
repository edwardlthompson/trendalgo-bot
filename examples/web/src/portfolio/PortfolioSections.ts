import { t } from "../i18n";
import { createTooltipHelp } from "../components/TooltipHelp";

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
  comparisons?: Array<{ label: string; title: string; pnl_usd: number; pnl_pct: number }>;
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
  };
  bot: Record<string, unknown>;
};

export type PortfolioCallbacks = {
  onSync: () => void;
  onSelectDate: (date: string) => void;
  onOpenInbox: () => void;
};

export function createPortfolioHero(data: PortfolioOverviewData): HTMLElement {
  const hero = document.createElement("section");
  hero.className = "gp-portfolio-hero";
  hero.dataset.testid = "portfolio-hero";
  const sign = data.daily_pnl_usd >= 0 ? "+" : "";
  hero.innerHTML = `
    <h2 class="gp-panel-title">${t("portfolio.title")}</h2>
    <p class="gp-net-worth" data-testid="net-worth">$${data.net_worth_usd.toFixed(2)}</p>
    <p class="gp-daily-pl" data-testid="daily-pl">${sign}$${data.daily_pnl_usd.toFixed(2)} (${sign}${(data.daily_pnl_pct * 100).toFixed(2)}%)</p>
    <p class="gp-health">${t("portfolio.health")}: ${data.health_score}/100 · ${t("health.drawdown")} ${(data.max_drawdown_pct * 100).toFixed(1)}%</p>
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
  syncBtn.textContent = t("portfolio.sync");
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

export function createHoldingsTable(holdings: Array<Record<string, number | string>>): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "gp-panel";
  wrap.dataset.testid = "holdings-table";
  wrap.innerHTML = `<h3>${t("portfolio.holdings")}</h3>`;
  const table = document.createElement("table");
  table.className = "gp-holdings-table";
  table.innerHTML = `
    <thead><tr>
      <th>${t("portfolio.col.asset")}</th><th>${t("portfolio.col.qty")}</th>
      <th>${t("portfolio.col.value")}</th><th>${t("portfolio.col.unrealized")}</th>
    </tr></thead><tbody></tbody>
  `;
  const tbody = table.querySelector("tbody")!;
  for (const h of holdings) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${h.asset}</td><td>${Number(h.quantity).toFixed(4)}</td>
      <td>$${Number(h.value_usd).toFixed(2)}</td>
      <td>$${Number(h.unrealized_pnl_usd ?? 0).toFixed(2)}</td>
    `;
    tbody.appendChild(tr);
  }
  wrap.appendChild(table);
  wrap.appendChild(createTooltipHelp(t("portfolio.tooltip.holdings")));
  return wrap;
}

export function createAllocationSection(
  allocation: Array<{ asset: string; value_usd: number; pct: number }>,
): HTMLElement {
  const section = document.createElement("div");
  section.className = "gp-panel";
  section.dataset.testid = "allocation-chart";
  section.innerHTML = `<h3>${t("portfolio.allocation")}</h3>`;
  const bars = document.createElement("div");
  bars.className = "gp-allocation-bars";
  for (const row of allocation) {
    const bar = document.createElement("div");
    bar.className = "gp-alloc-row";
    bar.innerHTML = `
      <span>${row.asset}</span>
      <div class="gp-alloc-bar" style="width:${Math.max(row.pct * 100, 4)}%"></div>
      <span>${(row.pct * 100).toFixed(1)}%</span>
    `;
    bars.appendChild(bar);
  }
  section.appendChild(bars);
  return section;
}

export function createPlBreakdown(pl: PortfolioOverviewData["pl_breakdown"]): HTMLElement {
  const section = document.createElement("div");
  section.className = "gp-panel";
  section.dataset.testid = "pl-breakdown";
  section.innerHTML = `
    <h3>${t("portfolio.pl_breakdown")}</h3>
    <dl class="gp-stat-grid">
      <div><dt>${t("portfolio.realized")}</dt><dd>$${pl.realized_usd.toFixed(2)}</dd></div>
      <div><dt>${t("portfolio.unrealized")}</dt><dd>$${pl.unrealized_usd.toFixed(2)}</dd></div>
      <div><dt>${t("portfolio.total_pl")}</dt><dd>$${pl.total_usd.toFixed(2)}</dd></div>
    </dl>
  `;
  return section;
}

export function createPeriodComparison(
  periods: PortfolioOverviewData["periods"],
): HTMLElement {
  const section = document.createElement("div");
  section.className = "gp-panel";
  section.dataset.testid = "period-comparison";
  section.innerHTML = `<h3>${t("portfolio.periods")}</h3><ul class="gp-period-list"></ul>`;
  const ul = section.querySelector("ul")!;
  for (const p of periods) {
    const li = document.createElement("li");
    li.textContent = `${p.label}: $${p.pnl_usd.toFixed(2)} (${(p.pnl_pct * 100).toFixed(2)}%)`;
    ul.appendChild(li);
  }
  return section;
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
      <div><dt>${t("dashboard.equity")}</dt><dd>$${Number(bot.equity_usd ?? 0).toFixed(2)}</dd></div>
      <div><dt>${t("dashboard.open_trades")}</dt><dd>${Array.isArray(bot.open_trades) ? bot.open_trades.length : 0}</dd></div>
    </dl>
  `;
  return section;
}
