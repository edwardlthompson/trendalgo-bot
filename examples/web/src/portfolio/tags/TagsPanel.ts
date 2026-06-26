import { t } from "../../i18n";

export function createTagsPanel(
  holdings: Array<{ asset: string; tag?: string }>,
  onFilter: (tag: string | null) => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "portfolio-tags";
  section.innerHTML = `<h3>${t("portfolio.tags")}</h3>`;
  const tags = [...new Set(holdings.map((h) => h.tag ?? "Other"))];
  const row = document.createElement("div");
  row.className = "gp-panel-actions";
  const allBtn = document.createElement("button");
  allBtn.type = "button";
  allBtn.className = "gp-btn-secondary";
  allBtn.textContent = t("portfolio.tags_all");
  allBtn.addEventListener("click", () => onFilter(null));
  row.appendChild(allBtn);
  for (const tag of tags) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "gp-btn-secondary";
    btn.dataset.testid = `tag-${tag}`;
    btn.textContent = tag;
    btn.addEventListener("click", () => onFilter(tag));
    row.appendChild(btn);
  }
  section.appendChild(row);
  return section;
}
