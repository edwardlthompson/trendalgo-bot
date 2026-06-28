import { t } from "../i18n";
import { buildExchangeSegments, sortAccountsByValue } from "../icons/exchangeSegments";
import { exchangeMeta, loadExchangeIcons } from "../icons/iconRegistry";

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

function createStackedBar(
  segments: ReturnType<typeof buildExchangeSegments>,
  totalUsd: number,
): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "gp-exchange-stack";
  wrap.dataset.testid = "exchange-portfolio-stack";

  const label = document.createElement("div");
  label.className = "gp-exchange-stack-header";
  label.innerHTML = `
    <span class="gp-exchange-stack-title">${t("portfolio.total_by_exchange")}</span>
    <span class="gp-exchange-stack-total">$${totalUsd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
  `;
  wrap.appendChild(label);

  const bar = document.createElement("div");
  bar.className = "gp-exchange-stack-bar";
  bar.setAttribute("role", "img");
  bar.setAttribute(
    "aria-label",
    segments.map((s) => `${s.brand} ${(s.pct * 100).toFixed(1)}%`).join(", "),
  );
  for (const seg of segments) {
    if (seg.widthPct <= 0) continue;
    const piece = document.createElement("div");
    piece.className = "gp-exchange-stack-segment";
    piece.style.width = `${seg.widthPct}%`;
    piece.style.backgroundColor = seg.color;
    piece.title = `${seg.brand}: ${(seg.pct * 100).toFixed(1)}% ($${seg.total_usd.toFixed(2)})`;
    bar.appendChild(piece);
  }
  wrap.appendChild(bar);
  return wrap;
}

function createAccountRow(
  acc: AccountSummary,
  pct: number,
  meta: ReturnType<typeof exchangeMeta>,
): HTMLElement {
  const li = document.createElement("li");
  li.className = "gp-exchange-row";
  li.dataset.testid = `exchange-account-${acc.exchange}`;

  const icon = document.createElement("img");
  icon.className = "gp-exchange-icon";
  icon.src = meta.icon;
  icon.alt = meta.brand;
  icon.width = 28;
  icon.height = 28;
  icon.loading = "lazy";

  const metaCol = document.createElement("div");
  metaCol.className = "gp-exchange-meta";
  metaCol.innerHTML = `
    <span class="gp-exchange-name">${meta.brand}</span>
    <span class="gp-exchange-sub">${acc.label} · ${acc.account_type} · ${acc.holdings_count} ${t("portfolio.holdings_short")}</span>
  `;

  const barWrap = document.createElement("div");
  barWrap.className = "gp-exchange-bar-wrap";
  const bar = document.createElement("div");
  bar.className = "gp-exchange-bar";
  bar.style.width = `${Math.max(pct * 100, 0.5)}%`;
  bar.style.backgroundColor = meta.color;
  const pctLabel = document.createElement("span");
  pctLabel.className = "gp-exchange-pct";
  pctLabel.textContent = `${(pct * 100).toFixed(1)}%`;
  barWrap.append(bar, pctLabel);

  const usd = document.createElement("span");
  usd.className = "gp-exchange-usd";
  usd.textContent = `$${acc.total_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  li.append(icon, metaCol, barWrap, usd);
  return li;
}

export async function createAccountsPanel(
  accounts: AccountSummary[],
  totalUsd: number,
  registry?: ExchangeRegistryEntry[],
): Promise<HTMLElement> {
  const iconRegistry = await loadExchangeIcons();
  const sorted = sortAccountsByValue(accounts);
  const segments = buildExchangeSegments(sorted, totalUsd, iconRegistry);

  const section = document.createElement("section");
  section.className = "gp-panel gp-exchange-accounts-panel";
  section.dataset.testid = "portfolio-accounts";
  section.innerHTML = `<h3>${t("portfolio.accounts")}</h3>`;

  section.appendChild(createStackedBar(segments, totalUsd));

  if (registry?.length) {
    const meta = document.createElement("p");
    meta.className = "gp-muted";
    meta.dataset.testid = "portfolio-registry-meta";
    const enabled = registry.filter((e) => e.portfolio_enabled).map((e) => e.brand).join(", ");
    meta.textContent = `${t("portfolio.registry_enabled")}: ${enabled}`;
    section.appendChild(meta);
  }

  const list = document.createElement("ul");
  list.className = "gp-exchange-list";
  for (const seg of segments) {
    const acc = sorted.find((a) => a.exchange === seg.exchange);
    if (!acc) continue;
    list.appendChild(createAccountRow(acc, seg.pct, exchangeMeta(iconRegistry, acc.exchange)));
  }
  section.appendChild(list);
  return section;
}

/** Sync wrapper for callers that cannot await panel construction. */
export function mountAccountsPanel(
  mount: HTMLElement,
  accounts: AccountSummary[],
  totalUsd: number,
  registry?: ExchangeRegistryEntry[],
): void {
  void createAccountsPanel(accounts, totalUsd, registry).then((panel) => {
    mount.replaceChildren(panel);
  });
}
