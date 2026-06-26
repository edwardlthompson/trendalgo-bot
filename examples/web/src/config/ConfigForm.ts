import { t } from "../i18n";

export type ExitRulesState = {
  trailing_stop_pct: number;
  scale_out_pct: number;
  scale_in_enabled: boolean;
  scale_out_enabled: boolean;
};

export type ConfigFormCallbacks = {
  onSave: (params: Record<string, number>) => void;
  onSaveExitRules?: (rules: ExitRulesState) => void;
};

export function createConfigForm(
  strategyId: string,
  params: Record<string, number>,
  pairs: string[],
  callbacks: ConfigFormCallbacks,
  exitRules?: ExitRulesState,
): HTMLElement {
  const form = document.createElement("form");
  form.className = "gp-panel";
  form.dataset.testid = "config-form";
  form.innerHTML = `<h2 class="gp-panel-title">${t("config.title")}</h2>`;

  const pairField = document.createElement("label");
  pairField.className = "gp-field";
  pairField.innerHTML = `<span>${t("config.pair")}</span>`;
  const pairSelect = document.createElement("select");
  pairSelect.dataset.testid = "config-pair";
  for (const pair of pairs) {
    const opt = document.createElement("option");
    opt.value = pair;
    opt.textContent = pair;
    pairSelect.appendChild(opt);
  }
  pairField.appendChild(pairSelect);
  form.appendChild(pairField);

  const fields: Array<[string, number]> = [
    ["rsi_entry", params.rsi_entry ?? 35],
    ["rsi_exit", params.rsi_exit ?? 65],
    ["lts_uniform_min", params.lts_uniform_min ?? 0.55],
  ];

  for (const [key, value] of fields) {
    const label = document.createElement("label");
    label.className = "gp-field";
    label.innerHTML = `<span>${t(`config.${key}`)}</span>`;
    const input = document.createElement("input");
    input.type = "number";
    input.name = key;
    input.value = String(value);
    input.step = key.includes("lts") ? "0.01" : "1";
    label.appendChild(input);
    form.appendChild(label);
  }

  if (exitRules) {
    const exitTitle = document.createElement("h3");
    exitTitle.className = "gp-panel-subtitle";
    exitTitle.textContent = t("config.exit_rules");
    form.appendChild(exitTitle);

    const trailing = document.createElement("label");
    trailing.className = "gp-field";
    trailing.innerHTML = `<span>${t("config.trailing_stop")}</span>`;
    const trailingInput = document.createElement("input");
    trailingInput.type = "number";
    trailingInput.name = "trailing_stop_pct";
    trailingInput.step = "0.01";
    trailingInput.value = String(exitRules.trailing_stop_pct);
    trailing.appendChild(trailingInput);
    form.appendChild(trailing);

    const scaleOut = document.createElement("label");
    scaleOut.className = "gp-field";
    scaleOut.innerHTML = `<span>${t("config.scale_out")}</span>`;
    const scaleOutInput = document.createElement("input");
    scaleOutInput.type = "number";
    scaleOutInput.name = "scale_out_pct";
    scaleOutInput.step = "0.1";
    scaleOutInput.value = String(exitRules.scale_out_pct);
    scaleOut.appendChild(scaleOutInput);
    form.appendChild(scaleOut);

    const scaleInToggle = document.createElement("label");
    scaleInToggle.className = "gp-field gp-settings-toggle";
    scaleInToggle.innerHTML = `<input type="checkbox" name="scale_in_enabled" ${exitRules.scale_in_enabled ? "checked" : ""} /><span>${t("config.scale_in")}</span>`;
    form.appendChild(scaleInToggle);

    const scaleOutToggle = document.createElement("label");
    scaleOutToggle.className = "gp-field gp-settings-toggle";
    scaleOutToggle.innerHTML = `<input type="checkbox" name="scale_out_enabled" ${exitRules.scale_out_enabled ? "checked" : ""} /><span>${t("config.scale_out_enabled")}</span>`;
    form.appendChild(scaleOutToggle);
  }

  const meta = document.createElement("p");
  meta.className = "gp-body";
  meta.textContent = `${t("config.strategy")}: ${strategyId}`;
  form.appendChild(meta);

  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const next: Record<string, number> = {};
    for (const [key] of fields) {
      const input = form.elements.namedItem(key) as HTMLInputElement | null;
      if (input) next[key] = Number(input.value);
    }
    callbacks.onSave(next);
    if (exitRules && callbacks.onSaveExitRules) {
      const trailingInput = form.elements.namedItem("trailing_stop_pct") as HTMLInputElement | null;
      const scaleOutInput = form.elements.namedItem("scale_out_pct") as HTMLInputElement | null;
      const scaleIn = form.elements.namedItem("scale_in_enabled") as HTMLInputElement | null;
      const scaleOut = form.elements.namedItem("scale_out_enabled") as HTMLInputElement | null;
      callbacks.onSaveExitRules({
        trailing_stop_pct: Number(trailingInput?.value ?? exitRules.trailing_stop_pct),
        scale_out_pct: Number(scaleOutInput?.value ?? exitRules.scale_out_pct),
        scale_in_enabled: scaleIn?.checked ?? false,
        scale_out_enabled: scaleOut?.checked ?? true,
      });
    }
  });

  const save = document.createElement("button");
  save.type = "submit";
  save.className = "gp-btn-primary";
  save.textContent = t("config.save");
  form.appendChild(save);
  return form;
}
