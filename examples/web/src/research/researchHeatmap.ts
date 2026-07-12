/** Heatmap table renderer for research tools. */

export function renderHeatmapChart(matrix: number[][], assets: string[]): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "gp-research-heatmap";
  wrap.dataset.testid = "research-heatmap-chart";
  const table = document.createElement("table");
  table.className = "gp-heatmap-table";
  const head = document.createElement("tr");
  head.appendChild(document.createElement("th"));
  for (const a of assets) {
    const th = document.createElement("th");
    th.textContent = a;
    head.appendChild(th);
  }
  table.appendChild(head);
  matrix.forEach((row, i) => {
    const tr = document.createElement("tr");
    const th = document.createElement("th");
    th.textContent = assets[i] ?? String(i);
    tr.appendChild(th);
    for (const v of row) {
      const td = document.createElement("td");
      const n = Number(v);
      const intensity = Math.min(1, Math.abs(n));
      td.textContent = n.toFixed(2);
      td.style.background = `color-mix(in srgb, var(--gp-color-primary) ${Math.round(intensity * 55)}%, transparent)`;
      tr.appendChild(td);
    }
    table.appendChild(tr);
  });
  wrap.appendChild(table);
  return wrap;
}
