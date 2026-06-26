import { t } from "../i18n";

export function createDiversificationPanel(
  suggestions: string[],
  matrix: { assets: string[]; matrix: number[][] },
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "diversification-panel";
  section.innerHTML = `<h3>${t("research.diversification")}</h3>`;
  const ul = document.createElement("ul");
  for (const tip of suggestions) {
    const li = document.createElement("li");
    li.textContent = tip;
    ul.appendChild(li);
  }
  section.appendChild(ul);
  const table = document.createElement("table");
  table.className = "gp-corr-table";
  table.dataset.testid = "correlation-matrix";
  const header = document.createElement("tr");
  for (const a of matrix.assets) {
    const th = document.createElement("th");
    th.textContent = a;
    header.appendChild(th);
  }
  table.appendChild(header);
  matrix.assets.forEach((_, i) => {
    const tr = document.createElement("tr");
    matrix.matrix[i].forEach((v) => {
      const td = document.createElement("td");
      td.textContent = v.toFixed(2);
      tr.appendChild(td);
    });
    table.appendChild(tr);
  });
  section.appendChild(table);
  return section;
}
