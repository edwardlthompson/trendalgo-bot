import { t } from "../i18n";

export type AppView =
  | "portfolio"
  | "dashboard"
  | "backtest"
  | "export"
  | "billing"
  | "scanner"
  | "debug"
  | "glossary"
  | "settings";

/** Primary tabs — keep mobile density low. */
const PRIMARY_VIEWS: AppView[] = ["portfolio", "dashboard", "scanner", "backtest"];

/** Overflow under More menu. */
const MORE_VIEWS: AppView[] = ["glossary", "export", "billing", "settings", "debug"];

function makeNavBtn(view: AppView, active: AppView, onSelect: (view: AppView) => void): HTMLButtonElement {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "gp-nav-btn";
  btn.dataset.view = view;
  btn.textContent = t(`nav.${view}`);
  btn.setAttribute("aria-current", active === view ? "page" : "false");
  btn.addEventListener("click", () => onSelect(view));
  return btn;
}

export function createMobileNav(
  active: AppView,
  onSelect: (view: AppView) => void,
): HTMLElement {
  const nav = document.createElement("nav");
  nav.className = "gp-mobile-nav";
  nav.setAttribute("aria-label", t("nav.label"));
  nav.dataset.testid = "mobile-nav";

  for (const view of PRIMARY_VIEWS) {
    nav.appendChild(makeNavBtn(view, active, onSelect));
  }

  const moreWrap = document.createElement("div");
  moreWrap.className = "gp-nav-more";
  moreWrap.dataset.testid = "nav-more";

  const moreBtn = document.createElement("button");
  moreBtn.type = "button";
  moreBtn.className = "gp-nav-btn";
  moreBtn.textContent = t("nav.more");
  moreBtn.setAttribute("aria-expanded", "false");
  moreBtn.setAttribute("aria-haspopup", "true");
  moreBtn.dataset.testid = "nav-more-btn";

  const menu = document.createElement("div");
  menu.className = "gp-nav-more-menu";
  menu.hidden = true;
  menu.setAttribute("role", "menu");
  const moreActive = MORE_VIEWS.includes(active);
  if (moreActive) moreBtn.setAttribute("aria-current", "page");

  for (const view of MORE_VIEWS) {
    const item = makeNavBtn(view, active, (v) => {
      menu.hidden = true;
      moreBtn.setAttribute("aria-expanded", "false");
      onSelect(v);
    });
    item.setAttribute("role", "menuitem");
    menu.appendChild(item);
  }

  moreBtn.addEventListener("click", () => {
    const open = menu.hidden;
    menu.hidden = !open;
    moreBtn.setAttribute("aria-expanded", open ? "true" : "false");
  });

  moreWrap.append(moreBtn, menu);
  nav.appendChild(moreWrap);
  return nav;
}
