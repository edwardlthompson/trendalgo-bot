import { t } from "../i18n";

const STORAGE_KEY = "trendalgo.onboarding.dismissed";

export function createOnboardingChecklist(opts: {
  hasPortfolio: boolean;
  hasBots: boolean;
  onGoScanner: () => void;
  onGoBots: () => void;
  onGoBacktest: () => void;
  onDismiss: () => void;
}): HTMLElement | null {
  if (localStorage.getItem(STORAGE_KEY) === "1") return null;
  if (opts.hasPortfolio && opts.hasBots) return null;

  const section = document.createElement("section");
  section.className = "gp-panel gp-onboarding";
  section.dataset.testid = "onboarding-checklist";
  section.innerHTML = `<h2 class="gp-panel-title">${t("onboarding.title")}</h2>
    <p class="gp-body">${t("onboarding.intro")}</p>`;

  const steps: Array<{ ok: boolean; label: string; action?: () => void; cta?: string }> = [
    { ok: opts.hasPortfolio, label: t("onboarding.step_portfolio") },
    {
      ok: false,
      label: t("onboarding.step_scanner"),
      action: opts.onGoScanner,
      cta: t("onboarding.go_scanner"),
    },
    {
      ok: opts.hasBots,
      label: t("onboarding.step_bot"),
      action: opts.onGoBots,
      cta: t("onboarding.go_bots"),
    },
    {
      ok: false,
      label: t("onboarding.step_backtest"),
      action: opts.onGoBacktest,
      cta: t("onboarding.go_backtest"),
    },
  ];

  const list = document.createElement("ol");
  list.className = "gp-onboarding-list";
  for (const step of steps) {
    const li = document.createElement("li");
    li.textContent = `${step.ok ? "✓ " : "○ "}${step.label}`;
    if (!step.ok && step.action && step.cta) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "gp-btn-secondary";
      btn.textContent = step.cta;
      btn.addEventListener("click", step.action);
      li.appendChild(btn);
    }
    list.appendChild(li);
  }
  section.appendChild(list);

  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "gp-btn-secondary";
  dismiss.dataset.testid = "onboarding-dismiss";
  dismiss.textContent = t("onboarding.dismiss");
  dismiss.addEventListener("click", () => {
    localStorage.setItem(STORAGE_KEY, "1");
    opts.onDismiss();
  });
  section.appendChild(dismiss);
  return section;
}
