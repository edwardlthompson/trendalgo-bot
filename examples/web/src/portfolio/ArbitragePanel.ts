import { t } from "../i18n";

export type ArbitrageAlert = {
  pair: string;
  spread_pct: number;
  buy_exchange: string;
  sell_exchange: string;
  informational_only: boolean;
};

export function createArbitragePanel(
  alerts: ArbitrageAlert[],
  disclaimer: string,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "portfolio-arbitrage";
  section.innerHTML = `<h3>${t("portfolio.arbitrage")}</h3><p class="gp-disclaimer">${disclaimer}</p>`;
  const list = document.createElement("ul");
  for (const a of alerts) {
    const li = document.createElement("li");
    li.textContent = `${a.pair}: ${(a.spread_pct * 100).toFixed(2)}% — buy ${a.buy_exchange}, sell ${a.sell_exchange}`;
    list.appendChild(li);
  }
  if (!alerts.length) {
    list.innerHTML = `<li>${t("portfolio.arbitrage_none")}</li>`;
  }
  section.appendChild(list);
  return section;
}
