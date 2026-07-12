import { t } from "../i18n";

/** Informational go-live checklist (hard gates remain HUMAN). */
export function createGoLiveWizard(opts: {
  dryRun: boolean;
  hasKeysHint: boolean;
}): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "go-live-wizard";
  section.innerHTML = `<h3>${t("go_live.title")}</h3><p class="gp-body">${t("go_live.intro")}</p>`;
  const list = document.createElement("ul");
  const rows: Array<[boolean, string]> = [
    [opts.dryRun, t("go_live.dry_run")],
    [opts.hasKeysHint, t("go_live.keys")],
    [false, t("go_live.attorney")],
    [false, t("go_live.approve")],
  ];
  for (const [ok, label] of rows) {
    const li = document.createElement("li");
    li.textContent = `${ok ? "✓" : "○"} ${label}`;
    list.appendChild(li);
  }
  section.appendChild(list);
  return section;
}
