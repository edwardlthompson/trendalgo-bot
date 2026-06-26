import { t } from "../i18n";

export type HealthSnapshot = {
  equity_usd: number;
  drawdown_pct: number;
  open_exposure_usd: number;
  bot_count: number;
  can_trade: boolean;
  dry_run: boolean;
  paused: boolean;
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
  el.innerHTML = `
    <h2 class="gp-health-title">${t("health.title")}</h2>
    <dl class="gp-health-grid">
      <div><dt>${t("health.equity")}</dt><dd>$${data.equity_usd.toFixed(2)}</dd></div>
      <div><dt>${t("health.drawdown")}</dt><dd>${(data.drawdown_pct * 100).toFixed(1)}%</dd></div>
      <div><dt>${t("health.exposure")}</dt><dd>$${data.open_exposure_usd.toFixed(2)}</dd></div>
      <div><dt>${t("health.bots")}</dt><dd>${data.bot_count}</dd></div>
    </dl>
    <p class="gp-health-status" data-testid="health-status">${t(statusKey)} · ${data.dry_run ? t("health.dry_run") : t("health.live")}</p>
  `;
  return el;
}
