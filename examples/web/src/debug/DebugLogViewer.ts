import { t } from "../i18n";

export function createDebugLogViewer(logs: string[]): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "debug-log-viewer";
  section.innerHTML = `<h2 class="gp-panel-title">${t("debug.title")}</h2>`;
  const pre = document.createElement("pre");
  pre.className = "gp-log-view";
  pre.dataset.testid = "debug-logs";
  pre.textContent = logs.length ? logs.join("\n") : t("debug.empty");
  section.appendChild(pre);
  return section;
}
