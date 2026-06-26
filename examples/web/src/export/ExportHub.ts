import { t } from "../i18n";

export type ExportItem = { id: string; path: string; format: string };

export function createExportHub(
  items: ExportItem[],
  onDownload: (path: string, id: string) => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "export-hub";
  section.innerHTML = `<h2 class="gp-panel-title">${t("export.title")}</h2><p class="gp-disclaimer">${t("export.disclaimer")}</p>`;
  const list = document.createElement("ul");
  list.className = "gp-export-list";
  for (const item of items) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "gp-btn-secondary";
    btn.dataset.testid = `export-${item.id}`;
    btn.textContent = `${item.id} (${item.format})`;
    btn.addEventListener("click", () => onDownload(item.path, item.id));
    li.appendChild(btn);
    list.appendChild(li);
  }
  section.appendChild(list);
  return section;
}
