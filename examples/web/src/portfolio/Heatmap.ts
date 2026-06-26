import { t } from "../i18n";

export type HeatmapRow = { asset: string; return_pct: number; volatility_pct: number };

export function createHeatmap(rows: HeatmapRow[]): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "performance-heatmap";
  section.innerHTML = `<h3>${t("portfolio.heatmap")}</h3>`;
  const grid = document.createElement("div");
  grid.className = "gp-heatmap-grid";
  for (const row of rows) {
    const cell = document.createElement("div");
    const intensity = Math.min(Math.abs(row.return_pct) / 10, 1);
    const positive = row.return_pct >= 0;
    cell.className = "gp-heatmap-cell";
    cell.style.opacity = String(0.4 + intensity * 0.6);
    cell.style.background = positive
      ? "var(--gp-color-primary)"
      : "var(--gp-color-error)";
    cell.innerHTML = `<strong>${row.asset}</strong><br>${row.return_pct.toFixed(1)}%`;
    grid.appendChild(cell);
  }
  section.appendChild(grid);
  return section;
}
