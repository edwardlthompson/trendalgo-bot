import type { DashboardData } from "../api/client";
import { t } from "../i18n";

export function createBotDashboard(data: DashboardData): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "bot-dashboard";
  const trades = data.open_trades.length;
  const orders = data.open_orders.length;
  section.innerHTML = `
    <h2 class="gp-panel-title">${t("dashboard.title")}</h2>
    <dl class="gp-stat-grid">
      <div><dt>${t("dashboard.equity")}</dt><dd>$${data.equity_usd.toFixed(2)}</dd></div>
      <div><dt>${t("dashboard.pair")}</dt><dd>${data.pair}</dd></div>
      <div><dt>${t("dashboard.strategy")}</dt><dd>${data.strategy_id}</dd></div>
      <div><dt>${t("dashboard.open_trades")}</dt><dd>${trades}</dd></div>
      <div><dt>${t("dashboard.open_orders")}</dt><dd>${orders}</dd></div>
      <div><dt>${t("health.bots")}</dt><dd>${data.bot_count}</dd></div>
      <div><dt>${t("dashboard.mode")}</dt><dd>${data.dry_run ? t("health.dry_run") : t("health.live")}</dd></div>
      <div><dt>${t("dashboard.engine")}</dt><dd><span class="gp-badge gp-badge-native">native</span></dd></div>
    </dl>
  `;
  if (data.bots?.length) {
    const multi = document.createElement("div");
    multi.dataset.testid = "multi-bot-list";
    multi.innerHTML = `<h3>${t("bots.title")}</h3><ul class="gp-bot-list"></ul>`;
    const ul = multi.querySelector("ul")!;
    for (const bot of data.bots) {
      const li = document.createElement("li");
      const engine = bot.engine ?? "native";
      li.innerHTML = `${bot.label}: ${bot.strategy_id} · ${bot.pair} · $${bot.equity_usd.toFixed(0)} · <span class="gp-badge gp-badge-native">${engine}</span> ${bot.enabled ? "" : "(off)"}`;
      ul.appendChild(li);
    }
    section.appendChild(multi);
  }
  return section;
}
