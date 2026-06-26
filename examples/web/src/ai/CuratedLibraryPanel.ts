import { t } from "../i18n";

export type CuratedPreset = {
  id: string;
  label: string;
  strategy_id: string;
  version: string;
};

export function createCuratedLibraryPanel(
  presets: CuratedPreset[],
  version: string,
  onDeploy: (strategyId: string) => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "curated-library";
  section.innerHTML = `<h3>${t("ai.curated")}</h3><p class="gp-body">v${version} — operator-maintained only</p>`;
  const list = document.createElement("ul");
  for (const p of presets) {
    const li = document.createElement("li");
    li.textContent = `${p.label} → ${p.strategy_id}`;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "gp-btn-secondary";
    btn.textContent = t("strategies.deploy");
    btn.addEventListener("click", () => onDeploy(p.strategy_id));
    li.appendChild(btn);
    list.appendChild(li);
  }
  section.appendChild(list);
  return section;
}
