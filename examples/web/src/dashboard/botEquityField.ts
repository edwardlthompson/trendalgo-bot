import type { BotEquityLimits } from "../api/client";
import { t } from "../i18n";

export type EquityMode = "base" | "quote" | "portfolio_pct";

export function normalizeEquityMode(mode: string | undefined): EquityMode {
  const raw = String(mode ?? "quote").toLowerCase();
  if (raw === "base") return "base";
  if (raw === "pct" || raw === "portfolio_pct" || raw === "portfolio") return "portfolio_pct";
  return "quote";
}

export function createBotEquityField(
  mode: EquityMode,
  value: number,
  limits: BotEquityLimits,
): { root: HTMLElement; syncMode: (next: EquityMode) => void; getValue: () => number; getMode: () => EquityMode } {
  const root = document.createElement("div");
  root.className = "gp-equity-row";

  const modeSelect = document.createElement("select");
  modeSelect.name = "equity_mode";
  modeSelect.dataset.testid = "bot-equity-mode";
  for (const opt of [
    { id: "base", label: t("bots.equity.base") },
    { id: "quote", label: t("bots.equity.quote") },
    { id: "portfolio_pct", label: t("bots.equity.portfolio_pct") },
  ] as const) {
    const el = document.createElement("option");
    el.value = opt.id;
    el.textContent = opt.label;
    if (opt.id === mode) el.selected = true;
    modeSelect.appendChild(el);
  }

  const valueInput = document.createElement("input");
  valueInput.name = "equity_input";
  valueInput.type = "number";
  valueInput.step = "any";
  valueInput.required = true;
  valueInput.dataset.testid = "bot-equity-input";
  valueInput.value = String(value);

  const hint = document.createElement("p");
  hint.className = "gp-equity-hint";
  hint.dataset.testid = "bot-equity-hint";

  let currentMode = mode;

  function applyConstraints(): void {
    valueInput.min = currentMode === "portfolio_pct" ? "0" : "0.00000001";
    if (currentMode === "portfolio_pct") {
      valueInput.max = "100";
      valueInput.step = "0.1";
      hint.textContent = t("bots.equity.hint_pct");
      return;
    }
    valueInput.removeAttribute("max");
    if (currentMode === "base") {
      const cap = limits.base.max;
      valueInput.max = String(Math.max(cap, 0));
      hint.textContent = `${limits.base.symbol} max: ${cap}`;
      return;
    }
    const cap = limits.quote.max;
    valueInput.max = String(Math.max(cap, 0));
    hint.textContent = `${limits.quote.symbol} max: ${cap}`;
  }

  function clampValue(): void {
    let n = Number(valueInput.value);
    if (!Number.isFinite(n) || n <= 0) return;
    if (currentMode === "portfolio_pct") {
      n = Math.min(100, Math.max(0, n));
    } else if (currentMode === "base") {
      n = Math.min(n, limits.base.max);
    } else {
      n = Math.min(n, limits.quote.max);
    }
    valueInput.value = String(n);
  }

  modeSelect.addEventListener("change", () => {
    currentMode = normalizeEquityMode(modeSelect.value);
    applyConstraints();
    clampValue();
  });

  valueInput.addEventListener("input", clampValue);
  valueInput.addEventListener("change", clampValue);

  root.innerHTML = `<label>${t("bots.field.equity_mode")}</label><label>${t("bots.field.equity_value")}</label>`;
  const labels = root.querySelectorAll("label");
  labels[0]?.appendChild(modeSelect);
  labels[1]?.appendChild(valueInput);
  root.appendChild(hint);
  applyConstraints();

  return {
    root,
    syncMode: (next) => {
      currentMode = next;
      modeSelect.value = next;
      applyConstraints();
    },
    getValue: () => Number(valueInput.value),
    getMode: () => currentMode,
  };
}

export function updateEquityLimits(
  field: ReturnType<typeof createBotEquityField>,
  limits: BotEquityLimits,
): void {
  const hint = field.root.querySelector(".gp-equity-hint") as HTMLElement | null;
  const input = field.root.querySelector("[name=equity_input]") as HTMLInputElement | null;
  if (!input || !hint) return;
  const mode = field.getMode();
  if (mode === "base") {
    input.max = String(Math.max(limits.base.max, 0));
    hint.textContent = `${limits.base.symbol} max: ${limits.base.max}`;
  } else if (mode === "quote") {
    input.max = String(Math.max(limits.quote.max, 0));
    hint.textContent = `${limits.quote.symbol} max: ${limits.quote.max}`;
  }
}
