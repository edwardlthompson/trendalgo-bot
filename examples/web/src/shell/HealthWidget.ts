import { t } from "../i18n";
import { formatUsd } from "../portfolio/formatUsd";

export type HealthSnapshot = {
  equity_usd: number;
  drawdown_pct: number;
  open_exposure_usd: number;
  bot_count: number;
  can_trade: boolean;
  dry_run: boolean;
  paused: boolean;
  net_worth_usd?: number;
  max_drawdown_pct?: number;
  health_score?: number;
};

export function createHealthWidget(data: HealthSnapshot): HTMLElement {
  const el = document.createElement("section");
  el.className = "gp-health-widget";
  el.dataset.testid = "health-widget";
  const statusKey = data.paused
    ? "health.status.paused"
    : data.can_trade
      ? "health.status.ok"
      : "health.status.blocked";

  const portfolioRows =
    data.net_worth_usd != null
      ? `
      <div><dt>${t("health.portfolio_value")}</dt><dd data-testid="health-portfolio-value">${formatUsd(data.net_worth_usd)}</dd></div>
      <div><dt>${t("health.portfolio_drawdown")}</dt><dd>${((data.max_drawdown_pct ?? 0) * 100).toFixed(1)}%</dd></div>
      <div><dt>${t("portfolio.health")}</dt><dd>${data.health_score ?? "—"}/100</dd></div>
    `
      : "";

  el.innerHTML = `
    <h2 class="gp-health-title">${t("health.title")}</h2>
    <dl class="gp-health-grid">
      ${portfolioRows}
      <div><dt>${t("health.bot_equity")}</dt><dd>${formatUsd(data.equity_usd)}</dd></div>
      <div><dt>${t("health.bot_drawdown")}</dt><dd>${(data.drawdown_pct * 100).toFixed(1)}%</dd></div>
      <div><dt>${t("health.exposure")}</dt><dd>${formatUsd(data.open_exposure_usd)}</dd></div>
      <div><dt>${t("health.bots")}</dt><dd>${data.bot_count}</dd></div>
    </dl>
    <p class="gp-health-status" data-testid="health-status">${t(statusKey)} · ${data.dry_run ? t("health.dry_run") : t("health.live")}</p>
  `;
  return el;
}
