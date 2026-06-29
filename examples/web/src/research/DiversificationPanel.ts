import { t } from "../i18n";

export type CorrelationMatrix = { assets: string[]; matrix: number[][] };

/** Map Pearson-style correlation (-1..1) to a readable heat cell color. */
export function correlationCellColor(value: number): string {
  const v = Math.max(-1, Math.min(1, value));
  const hue = ((v + 1) / 2) * 142;
  const light = 28 + Math.abs(v) * 14;
  return `hsl(${hue.toFixed(0)} 52% ${light.toFixed(0)}%)`;
}

function buildCorrelationTable(matrix: CorrelationMatrix): HTMLTableElement {
  const table = document.createElement("table");
  table.className = "gp-corr-table";
  table.dataset.testid = "correlation-matrix";

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  const corner = document.createElement("th");
  corner.className = "gp-corr-corner";
  corner.scope = "col";
  corner.textContent = "";
  headRow.appendChild(corner);
  for (const asset of matrix.assets) {
    const th = document.createElement("th");
    th.scope = "col";
    th.className = "gp-corr-col-head";
    th.textContent = asset;
    th.title = asset;
    headRow.appendChild(th);
  }
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  matrix.assets.forEach((rowAsset, i) => {
    const tr = document.createElement("tr");
    const rowHead = document.createElement("th");
    rowHead.scope = "row";
    rowHead.className = "gp-corr-row-head";
    rowHead.textContent = rowAsset;
    rowHead.title = rowAsset;
    tr.appendChild(rowHead);

    const row = matrix.matrix[i] ?? [];
    for (let j = 0; j < matrix.assets.length; j++) {
      const value = row[j] ?? 0;
      const td = document.createElement("td");
      td.className = "gp-corr-cell";
      td.textContent = value.toFixed(2);
      td.style.background = correlationCellColor(value);
      td.title = `${rowAsset} × ${matrix.assets[j]}: ${value.toFixed(2)}`;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  return table;
}

export function createDiversificationPanel(
  suggestions: string[],
  matrix: CorrelationMatrix,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel gp-diversification-panel";
  section.dataset.testid = "diversification-panel";

  const title = document.createElement("h3");
  title.className = "gp-panel-subtitle";
  title.textContent = t("research.diversification");
  section.appendChild(title);

  const tipsBlock = document.createElement("div");
  tipsBlock.className = "gp-diversification-suggestions";
  tipsBlock.innerHTML = `<h4 class="gp-panel-subtitle">${t("research.diversification_suggestions")}</h4>`;
  const ul = document.createElement("ul");
  ul.className = "gp-diversification-list";
  for (const tip of suggestions.length ? suggestions : [t("research.diversification_empty")]) {
    const li = document.createElement("li");
    li.textContent = tip;
    ul.appendChild(li);
  }
  tipsBlock.appendChild(ul);
  section.appendChild(tipsBlock);

  const matrixBlock = document.createElement("div");
  matrixBlock.className = "gp-diversification-matrix";
  matrixBlock.innerHTML = `<h4 class="gp-panel-subtitle">${t("research.correlation_matrix")}</h4>`;
  const wrap = document.createElement("div");
  wrap.className = "gp-corr-matrix-wrap";
  wrap.appendChild(buildCorrelationTable(matrix));
  matrixBlock.appendChild(wrap);
  const legend = document.createElement("p");
  legend.className = "gp-body gp-muted gp-corr-legend";
  legend.textContent = t("research.correlation_legend");
  matrixBlock.appendChild(legend);
  section.appendChild(matrixBlock);

  return section;
}
