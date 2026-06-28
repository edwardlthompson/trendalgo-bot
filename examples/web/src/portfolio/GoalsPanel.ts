import { t } from "../i18n";
import { formatUsd } from "./formatUsd";

export type GoalType =
  | "portfolio_growth"
  | "annual_return"
  | "monthly_return"
  | "capital_preservation"
  | "beat_btc"
  | "income";

export type GoalData = {
  label: string;
  target_net_worth_usd: number;
  progress_pct: number;
  remaining_usd: number;
  current_net_worth_usd: number;
  goal_type?: GoalType;
  horizon_months?: number;
  target_return_pct?: number;
};

export type GoalSavePayload = {
  goal_type: GoalType;
  horizon_months: number;
  target_net_worth_usd: number;
  target_return_pct: number;
  label: string;
};

const GOAL_TYPES: GoalType[] = [
  "portfolio_growth",
  "annual_return",
  "monthly_return",
  "capital_preservation",
  "beat_btc",
  "income",
];

const HORIZONS = [1, 3, 6, 12, 36, 60];

function usesPercentTarget(type: GoalType): boolean {
  return (
    type === "annual_return" ||
    type === "monthly_return" ||
    type === "capital_preservation" ||
    type === "beat_btc"
  );
}

function defaultLabel(type: GoalType): string {
  return t(`portfolio.goal_type.${type}`);
}

export function createGoalsPanel(
  goal: GoalData | null,
  onSave: (payload: GoalSavePayload) => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "portfolio-goals";
  section.innerHTML = `<h3>${t("portfolio.goals")}</h3>`;

  const form = document.createElement("form");
  form.className = "gp-goal-form";
  form.dataset.testid = "goal-form";

  const typeSelect = document.createElement("select");
  typeSelect.name = "goal_type";
  typeSelect.dataset.testid = "goal-type";
  for (const type of GOAL_TYPES) {
    const opt = document.createElement("option");
    opt.value = type;
    opt.textContent = t(`portfolio.goal_type.${type}`);
    typeSelect.appendChild(opt);
  }

  const horizonSelect = document.createElement("select");
  horizonSelect.name = "horizon_months";
  horizonSelect.dataset.testid = "goal-horizon";
  for (const months of HORIZONS) {
    const opt = document.createElement("option");
    opt.value = String(months);
    opt.textContent = t(`portfolio.goal_horizon.${months}`);
    horizonSelect.appendChild(opt);
  }

  const usdInput = document.createElement("input");
  usdInput.type = "number";
  usdInput.name = "target_net_worth_usd";
  usdInput.min = "1";
  usdInput.step = "100";
  usdInput.dataset.testid = "goal-target-usd";

  const pctInput = document.createElement("input");
  pctInput.type = "number";
  pctInput.name = "target_return_pct";
  pctInput.min = "0.1";
  pctInput.max = "100";
  pctInput.step = "0.1";
  pctInput.dataset.testid = "goal-target-pct";

  const pctWrap = document.createElement("label");
  pctWrap.className = "gp-goal-field gp-goal-pct-field";
  pctWrap.innerHTML = `<span>${t("portfolio.goal_target_pct")}</span>`;
  pctWrap.appendChild(pctInput);

  const usdWrap = document.createElement("label");
  usdWrap.className = "gp-goal-field gp-goal-usd-field";
  usdWrap.innerHTML = `<span>${t("portfolio.goal_target_usd")}</span>`;
  usdWrap.appendChild(usdInput);

  const syncTargetFields = (): void => {
    const type = typeSelect.value as GoalType;
    const pct = usesPercentTarget(type);
    pctWrap.hidden = !pct;
    usdWrap.hidden = pct && type !== "income";
    if (type === "capital_preservation") {
      pctWrap.querySelector("span")!.textContent = t("portfolio.goal_max_drawdown");
    } else if (type === "beat_btc") {
      pctWrap.querySelector("span")!.textContent = t("portfolio.goal_alpha_target");
    } else {
      pctWrap.querySelector("span")!.textContent = t("portfolio.goal_target_pct");
    }
  };

  typeSelect.addEventListener("change", syncTargetFields);

  form.append(
    field(t("portfolio.goal_type_label"), typeSelect),
    field(t("portfolio.goal_horizon_label"), horizonSelect),
    usdWrap,
    pctWrap,
  );

  const saveBtn = document.createElement("button");
  saveBtn.type = "submit";
  saveBtn.className = "gp-btn-primary";
  saveBtn.dataset.testid = "goal-save";
  saveBtn.textContent = t("portfolio.goal_save");
  form.appendChild(saveBtn);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const type = typeSelect.value as GoalType;
    onSave({
      goal_type: type,
      horizon_months: Number(horizonSelect.value),
      target_net_worth_usd: Number(usdInput.value) || goal?.current_net_worth_usd || 1000,
      target_return_pct: (Number(pctInput.value) || 0) / 100,
      label: defaultLabel(type),
    });
  });

  section.appendChild(form);

  if (goal) {
    typeSelect.value = goal.goal_type ?? "portfolio_growth";
    horizonSelect.value = String(goal.horizon_months ?? 12);
    usdInput.value = String(goal.target_net_worth_usd);
    pctInput.value = goal.target_return_pct ? String(goal.target_return_pct * 100) : "";
    syncTargetFields();

    const bar = document.createElement("div");
    bar.className = "gp-progress-bar";
    bar.dataset.testid = "goal-progress";
    const fill = document.createElement("div");
    fill.className = "gp-progress-fill";
    fill.style.width = `${Math.min(100, goal.progress_pct * 100)}%`;
    bar.appendChild(fill);

    const meta = document.createElement("p");
    meta.className = "gp-body gp-goal-progress-meta";
    meta.dataset.testid = "goal-progress-meta";
    const targetLabel = usesPercentTarget(typeSelect.value as GoalType)
      ? `${((goal.target_return_pct ?? 0) * 100).toFixed(1)}%`
      : formatUsd(goal.target_net_worth_usd);
    meta.textContent = `${goal.label}: ${formatUsd(goal.current_net_worth_usd)} → ${targetLabel} (${(goal.progress_pct * 100).toFixed(1)}%)`;
    section.append(bar, meta);
  } else {
    syncTargetFields();
    section.insertAdjacentHTML("beforeend", `<p>${t("portfolio.goals_empty")}</p>`);
  }

  return section;
}

function field(label: string, control: HTMLElement): HTMLElement {
  const wrap = document.createElement("label");
  wrap.className = "gp-goal-field";
  wrap.innerHTML = `<span>${label}</span>`;
  wrap.appendChild(control);
  return wrap;
}
