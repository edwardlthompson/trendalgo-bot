import { t } from "../i18n";

export type AccountSummary = {
  account_id: number;
  exchange: string;
  label: string;
  account_type: string;
  total_usd: number;
  holdings_count: number;
};

export type ExchangeRegistryEntry = {
  id: string;
  brand: string;
  tier: string;
  portfolio_enabled: boolean;
  trading_enabled: boolean;
  configured?: boolean;
};

export function createAccountsPanel(
  accounts: AccountSummary[],
  registry?: ExchangeRegistryEntry[],
): HTMLElement {
  const brandById = new Map(registry?.map((e) => [e.id, e.brand]) ?? []);
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "portfolio-accounts";
  section.innerHTML = `<h3>${t("portfolio.accounts")}</h3>`;
  if (registry?.length) {
    const meta = document.createElement("p");
    meta.className = "gp-muted";
    meta.dataset.testid = "portfolio-registry-meta";
    const enabled = registry.filter((e) => e.portfolio_enabled).map((e) => e.brand).join(", ");
    meta.textContent = `${t("portfolio.registry_enabled")}: ${enabled}`;
    section.appendChild(meta);
  }
  const list = document.createElement("ul");
  list.className = "gp-account-list";
  for (const acc of accounts) {
    const li = document.createElement("li");
    const brand = brandById.get(acc.exchange) ?? acc.exchange;
    li.textContent = `${brand} / ${acc.label} (${acc.account_type}) — $${acc.total_usd.toFixed(2)}`;
    list.appendChild(li);
  }
  section.appendChild(list);
  return section;
}
