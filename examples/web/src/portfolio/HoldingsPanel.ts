import { t } from "../i18n";
import { createTooltipHelp } from "../components/TooltipHelp";
import { coinIconUrl, loadCoinIcons } from "../icons/iconRegistry";
import { formatUsd } from "./formatUsd";
import {
  filterHoldings,
  sortHoldings,
  type HoldingsSortKey,
  type SortDirection,
} from "./holdingsSort";
import { holdingAllocationPct } from "./holdingAllocation";

export type HoldingsPanelOptions = {
  portfolioTotalUsd: number;
  tagFilter: string | null;
  onTagFilter: (tag: string | null) => void;
};

function createAllocationCell(pct: number, asset: string): HTMLTableCellElement {
  const td = document.createElement("td");
  td.className = "gp-holdings-alloc-cell";
  const track = document.createElement("div");
  track.className = "gp-holdings-alloc-track";
  track.setAttribute("role", "img");
  track.setAttribute("aria-label", `${asset} ${(pct * 100).toFixed(1)}% of portfolio`);
  const bar = document.createElement("div");
  bar.className = "gp-holdings-alloc-bar";
  bar.style.width = `${Math.max(pct * 100, pct > 0 ? 2 : 0)}%`;
  track.appendChild(bar);
  const label = document.createElement("span");
  label.className = "gp-holdings-alloc-pct";
  label.textContent = `${(pct * 100).toFixed(1)}%`;
  td.append(track, label);
  return td;
}

function createTagFilters(
  holdings: Array<Record<string, number | string>>,
  tagFilter: string | null,
  onTagFilter: (tag: string | null) => void,
): HTMLElement {
  const row = document.createElement("div");
  row.className = "gp-holdings-tag-filters";
  row.dataset.testid = "holdings-tag-filters";
  const tags = [...new Set(holdings.map((h) => String(h.tag ?? "Other")))].sort();
  const mkBtn = (label: string, tag: string | null, testId: string): HTMLButtonElement => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "gp-btn-secondary gp-tag-filter-btn";
    btn.dataset.testid = testId;
    btn.textContent = label;
    btn.setAttribute("aria-pressed", String(tagFilter === tag));
    btn.classList.toggle("gp-tag-filter-active", tagFilter === tag);
    btn.addEventListener("click", () => onTagFilter(tag));
    return btn;
  };
  row.append(
    mkBtn(t("portfolio.tags_all"), null, "holdings-tag-all"),
    ...tags.map((tag) => mkBtn(tag, tag, `holdings-tag-${tag}`)),
  );
  return row;
}

export async function createHoldingsPanel(
  holdings: Array<Record<string, number | string>>,
  options: HoldingsPanelOptions,
): Promise<HTMLElement> {
  const coinRegistry = await loadCoinIcons();
  const wrap = document.createElement("div");
  wrap.className = "gp-panel";
  wrap.dataset.testid = "holdings-table";

  const toolbar = document.createElement("div");
  toolbar.className = "gp-holdings-toolbar";
  const title = document.createElement("h3");
  title.textContent = t("portfolio.holdings_allocation");
  const dustLabel = document.createElement("label");
  dustLabel.className = "gp-holdings-dust-toggle";
  const hideDustCheckbox = document.createElement("input");
  hideDustCheckbox.type = "checkbox";
  hideDustCheckbox.dataset.testid = "holdings-hide-dust";
  dustLabel.append(hideDustCheckbox, document.createTextNode(` ${t("portfolio.hide_dust")}`));
  toolbar.append(title, dustLabel);
  wrap.appendChild(toolbar);
  wrap.appendChild(createTagFilters(holdings, options.tagFilter, options.onTagFilter));

  let sortKey: HoldingsSortKey = "value";
  let sortDirection: SortDirection = "desc";
  let hideDust = false;

  const table = document.createElement("table");
  table.className = "gp-holdings-table gp-holdings-table-compact";
  const colgroup = document.createElement("colgroup");
  colgroup.innerHTML = `
    <col class="gp-col-asset" />
    <col class="gp-col-allocation" />
    <col class="gp-col-qty" />
    <col class="gp-col-value" />
    <col class="gp-col-unrealized" />
  `;
  table.appendChild(colgroup);

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  const tbody = document.createElement("tbody");

  const assetTh = document.createElement("th");
  assetTh.textContent = t("portfolio.col.asset");
  const allocTh = document.createElement("th");
  allocTh.textContent = t("portfolio.col.allocation");
  const qtyTh = document.createElement("th");
  qtyTh.textContent = t("portfolio.col.qty");

  const valueSortBtn = document.createElement("button");
  valueSortBtn.type = "button";
  valueSortBtn.className = "gp-holdings-sort";
  valueSortBtn.dataset.testid = "holdings-sort-value";
  const unrealizedSortBtn = document.createElement("button");
  unrealizedSortBtn.type = "button";
  unrealizedSortBtn.className = "gp-holdings-sort";
  unrealizedSortBtn.dataset.testid = "holdings-sort-unrealized";

  const valueTh = document.createElement("th");
  valueTh.scope = "col";
  valueTh.appendChild(valueSortBtn);
  const unrealizedTh = document.createElement("th");
  unrealizedTh.scope = "col";
  unrealizedTh.appendChild(unrealizedSortBtn);

  headerRow.append(assetTh, allocTh, qtyTh, valueTh, unrealizedTh);
  thead.appendChild(headerRow);
  table.append(thead, tbody);

  function filteredHoldings(): Array<Record<string, number | string>> {
    const tagged =
      options.tagFilter
        ? holdings.filter((h) => String(h.tag ?? "Other") === options.tagFilter)
        : holdings;
    return filterHoldings(tagged, { hideDust });
  }

  function updateSortButtons(): void {
    const labels: Record<HoldingsSortKey, string> = {
      value: t("portfolio.col.value"),
      unrealized: t("portfolio.col.unrealized"),
    };
    const columns: Array<[HoldingsSortKey, HTMLButtonElement, HTMLTableCellElement]> = [
      ["value", valueSortBtn, valueTh],
      ["unrealized", unrealizedSortBtn, unrealizedTh],
    ];
    for (const [key, btn, th] of columns) {
      const active = sortKey === key;
      const arrow = active ? (sortDirection === "desc" ? " ↓" : " ↑") : "";
      btn.textContent = `${labels[key]}${arrow}`;
      th.setAttribute("aria-sort", active ? (sortDirection === "desc" ? "descending" : "ascending") : "none");
      btn.classList.toggle("gp-holdings-sort-active", active);
    }
  }

  function renderRows(): void {
    tbody.replaceChildren();
    for (const h of sortHoldings(filteredHoldings(), sortKey, sortDirection)) {
      const asset = String(h.asset);
      const valueUsd = Number(h.value_usd);
      const pct = holdingAllocationPct(valueUsd, options.portfolioTotalUsd);
      const iconSrc = coinIconUrl(coinRegistry, asset);
      const tr = document.createElement("tr");
      const assetCell = document.createElement("td");
      assetCell.className = "gp-asset-cell";
      if (iconSrc) {
        const img = document.createElement("img");
        img.className = "gp-coin-icon";
        img.src = iconSrc;
        img.alt = asset;
        img.width = 18;
        img.height = 18;
        img.loading = "lazy";
        assetCell.append(img, document.createTextNode(` ${asset}`));
      } else {
        assetCell.textContent = asset;
      }
      const qtyCell = document.createElement("td");
      qtyCell.className = "gp-holdings-qty-cell";
      qtyCell.textContent = Number(h.quantity).toFixed(4);
      const valueCell = document.createElement("td");
      valueCell.className = "gp-holdings-money-cell";
      valueCell.textContent = formatUsd(valueUsd);
      const unrealizedCell = document.createElement("td");
      unrealizedCell.className = "gp-holdings-money-cell";
      unrealizedCell.textContent = formatUsd(Number(h.unrealized_pnl_usd ?? 0));
      tr.append(
        assetCell,
        createAllocationCell(Number(pct), asset),
        qtyCell,
        valueCell,
        unrealizedCell,
      );
      tbody.appendChild(tr);
    }
    updateSortButtons();
  }

  function setSort(key: HoldingsSortKey): void {
    if (sortKey === key) {
      sortDirection = sortDirection === "desc" ? "asc" : "desc";
    } else {
      sortKey = key;
      sortDirection = "desc";
    }
    renderRows();
  }

  valueSortBtn.addEventListener("click", () => setSort("value"));
  unrealizedSortBtn.addEventListener("click", () => setSort("unrealized"));
  hideDustCheckbox.addEventListener("change", () => {
    hideDust = hideDustCheckbox.checked;
    renderRows();
  });
  renderRows();

  wrap.appendChild(table);
  wrap.appendChild(createTooltipHelp(t("portfolio.tooltip.holdings")));
  return wrap;
}

export function mountHoldingsPanel(
  mount: HTMLElement,
  holdings: Array<Record<string, number | string>>,
  options: HoldingsPanelOptions,
): void {
  void createHoldingsPanel(holdings, options).then((panel) => mount.replaceChildren(panel));
}
