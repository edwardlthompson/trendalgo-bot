import { t } from "../i18n";

export type HeatmapRow = { asset: string; return_pct: number; volatility_pct: number };

export function heatmapFromHoldings(
  holdings: Array<Record<string, number | string>>,
): HeatmapRow[] {
  return holdings.map((h) => {
    const pct = Number(h.pct_change ?? 0);
    return {
      asset: String(h.asset),
      return_pct: Math.round(pct * 10000) / 100,
      volatility_pct: Math.round(Math.abs(pct) * 10000) / 100,
    };
  });
}

/** Green (gains) → yellow (flat) → red (losses); magnitude caps at 20%. */
export function heatmapColor(returnPct: number): string {
  const cap = 20;
  const t = Math.max(-1, Math.min(1, returnPct / cap));
  const yellowHue = 48;
  const hue =
    t >= 0
      ? yellowHue + t * (142 - yellowHue)
      : yellowHue + t * yellowHue;
  const saturation = 52 + Math.abs(t) * 28;
  const lightness = 28 - Math.abs(t) * 8;
  return `hsl(${Math.round(hue)} ${Math.round(saturation)}% ${Math.round(lightness)}%)`;
}

export function createHeatmap(rows: HeatmapRow[]): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "performance-heatmap";
  section.innerHTML = `<h3>${t("portfolio.heatmap")}</h3>`;
  const grid = document.createElement("div");
  grid.className = "gp-heatmap-grid";
  const sorted = [...rows].sort((a, b) => b.return_pct - a.return_pct);
  for (const row of sorted) {
    const cell = document.createElement("div");
    cell.className = "gp-heatmap-cell";
    cell.style.background = heatmapColor(row.return_pct);
    cell.innerHTML = `<strong>${row.asset}</strong><br>${row.return_pct >= 0 ? "+" : ""}${row.return_pct.toFixed(1)}%`;
    grid.appendChild(cell);
  }
  section.appendChild(grid);
  return section;
}
