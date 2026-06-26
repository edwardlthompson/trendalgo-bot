import { t } from "../../i18n";

export type LibraryRun = {
  id: number;
  strategy: string;
  pair: string;
  tag: string | null;
  created_at: string;
};

export function createBacktestLibraryPanel(
  runs: LibraryRun[],
  onClone: (id: number) => void,
  onCompare: (ids: number[]) => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "backtest-library";
  section.innerHTML = `<h3>${t("backtest.library")}</h3>`;
  if (!runs.length) {
    section.innerHTML += `<p>${t("backtest.library_empty")}</p>`;
    return section;
  }
  const ul = document.createElement("ul");
  ul.className = "gp-library-list";
  const selected: number[] = [];
  for (const run of runs) {
    const li = document.createElement("li");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.addEventListener("change", () => {
      if (cb.checked) selected.push(run.id);
      else {
        const i = selected.indexOf(run.id);
        if (i >= 0) selected.splice(i, 1);
      }
    });
    li.append(cb, document.createTextNode(`${run.strategy} ${run.pair} · ${run.tag ?? "—"}`));
    const cloneBtn = document.createElement("button");
    cloneBtn.type = "button";
    cloneBtn.className = "gp-btn-secondary";
    cloneBtn.textContent = t("backtest.clone");
    cloneBtn.addEventListener("click", () => onClone(run.id));
    li.appendChild(cloneBtn);
    ul.appendChild(li);
  }
  section.appendChild(ul);
  const compareBtn = document.createElement("button");
  compareBtn.type = "button";
  compareBtn.className = "gp-btn-primary";
  compareBtn.dataset.testid = "backtest-compare";
  compareBtn.textContent = t("backtest.compare");
  compareBtn.addEventListener("click", () => onCompare(selected.slice(0, 5)));
  section.appendChild(compareBtn);
  return section;
}
