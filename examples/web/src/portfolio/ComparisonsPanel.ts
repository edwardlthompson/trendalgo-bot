import { t } from "../i18n";

export type ComparisonRow = {
  label: string;
  title: string;
  pnl_usd: number;
  pnl_pct: number;
};

export function createComparisonsPanel(rows: ComparisonRow[]): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "portfolio-comparisons";
  section.innerHTML = `<h3>${t("portfolio.comparisons")}</h3>`;
  const table = document.createElement("table");
  table.className = "gp-holdings-table";
  table.innerHTML = `<thead><tr><th>${t("portfolio.col.period")}</th><th>P/L</th><th>%</th></tr></thead><tbody></tbody>`;
  const tbody = table.querySelector("tbody")!;
  for (const row of rows) {
    const tr = document.createElement("tr");
    const sign = row.pnl_usd >= 0 ? "+" : "";
    tr.innerHTML = `<td>${row.title}</td><td>${sign}$${row.pnl_usd.toFixed(2)}</td><td>${sign}${(row.pnl_pct * 100).toFixed(2)}%</td>`;
    tbody.appendChild(tr);
  }
  section.appendChild(table);
  return section;
}
