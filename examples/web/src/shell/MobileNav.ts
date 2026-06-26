import { t } from "../i18n";

export type AppView =
  | "portfolio"
  | "dashboard"
  | "strategies"
  | "backtest"
  | "export"
  | "billing"
  | "scanner"
  | "risk"
  | "config"
  | "debug";

const VIEWS: AppView[] = [
  "portfolio",
  "dashboard",
  "strategies",
  "backtest",
  "export",
  "billing",
  "scanner",
  "risk",
  "config",
  "debug",
];

export function createMobileNav(
  active: AppView,
  onSelect: (view: AppView) => void,
): HTMLElement {
  const nav = document.createElement("nav");
  nav.className = "gp-mobile-nav";
  nav.setAttribute("aria-label", t("nav.label"));
  nav.dataset.testid = "mobile-nav";

  for (const view of VIEWS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "gp-nav-btn";
    btn.dataset.view = view;
    btn.textContent = t(`nav.${view}`);
    btn.setAttribute("aria-current", active === view ? "page" : "false");
    btn.addEventListener("click", () => onSelect(view));
    nav.appendChild(btn);
  }
  return nav;
}
