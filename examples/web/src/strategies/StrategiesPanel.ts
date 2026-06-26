import { t } from "../i18n";

export type StrategyTemplate = {
  id: string;
  description: string;
  kind: string;
  timeframes: string[];
};

export type StrategiesPanelCallbacks = {
  onDeploy: (strategyId: string) => void;
  onExport: (strategyId: string) => void;
  onImport: (json: string) => void;
  onCompose: (code: string) => void;
};

export function createStrategiesPanel(
  templates: StrategyTemplate[],
  composerCode: string,
  callbacks: StrategiesPanelCallbacks,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "strategies-panel";
  section.innerHTML = `<h2 class="gp-panel-title">${t("strategies.title")}</h2>`;

  const list = document.createElement("ul");
  list.className = "gp-template-list";
  list.dataset.testid = "template-list";
  for (const tpl of templates) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${tpl.id}</strong> <span class="gp-tag">${tpl.kind}</span><br>${tpl.description}`;
    const deploy = document.createElement("button");
    deploy.type = "button";
    deploy.className = "gp-btn-secondary";
    deploy.textContent = t("strategies.deploy");
    deploy.addEventListener("click", () => callbacks.onDeploy(tpl.id));
    const exportBtn = document.createElement("button");
    exportBtn.type = "button";
    exportBtn.className = "gp-btn-secondary";
    exportBtn.textContent = t("strategies.export");
    exportBtn.addEventListener("click", () => callbacks.onExport(tpl.id));
    li.append(deploy, exportBtn);
    list.appendChild(li);
  }
  section.appendChild(list);

  const composer = document.createElement("div");
  composer.className = "gp-composer";
  composer.dataset.testid = "strategy-composer";
  composer.innerHTML = `<h3>${t("strategies.composer")}</h3>`;
  const textarea = document.createElement("textarea");
  textarea.className = "gp-composer-code";
  textarea.rows = 6;
  textarea.value = composerCode;
  textarea.placeholder = t("strategies.composer_placeholder");
  const saveComposer = document.createElement("button");
  saveComposer.type = "button";
  saveComposer.className = "gp-btn-primary";
  saveComposer.textContent = t("strategies.composer_save");
  saveComposer.addEventListener("click", () => callbacks.onCompose(textarea.value));
  composer.append(textarea, saveComposer);
  section.appendChild(composer);

  const importArea = document.createElement("div");
  importArea.innerHTML = `<h3>${t("strategies.import")}</h3>`;
  const importInput = document.createElement("textarea");
  importInput.rows = 4;
  importInput.dataset.testid = "template-import";
  const importBtn = document.createElement("button");
  importBtn.type = "button";
  importBtn.className = "gp-btn-secondary";
  importBtn.textContent = t("strategies.import_btn");
  importBtn.addEventListener("click", () => callbacks.onImport(importInput.value));
  importArea.append(importInput, importBtn);
  section.appendChild(importArea);

  return section;
}
