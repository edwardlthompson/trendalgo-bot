import { t } from "../i18n";

let toastTimer: ReturnType<typeof setTimeout> | undefined;

/** Show a dismissible shell-level error/status toast (role=alert). */
export function showAppToast(message: string, kind: "error" | "info" = "error"): void {
  let el = document.querySelector<HTMLElement>("[data-testid='app-toast']");
  if (!el) {
    el = document.createElement("div");
    el.className = "gp-app-toast";
    el.dataset.testid = "app-toast";
    el.setAttribute("role", "alert");
    document.body.appendChild(el);
  }
  el.dataset.kind = kind;
  el.hidden = false;
  el.textContent = message;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el!.hidden = true;
  }, 6000);
}

export function createBootSkeleton(): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "gp-boot-skeleton";
  wrap.dataset.testid = "boot-skeleton";
  wrap.innerHTML = `
    <p class="gp-body">${t("app.loading")}</p>
    <div class="gp-skeleton-block" aria-hidden="true"></div>
    <div class="gp-skeleton-block gp-skeleton-short" aria-hidden="true"></div>
  `;
  return wrap;
}

export function createRiskBadge(opts: {
  dryRun: boolean;
  paused: boolean;
  canTrade: boolean;
}): HTMLElement {
  const badge = document.createElement("span");
  badge.className = "gp-risk-badge";
  badge.dataset.testid = "risk-badge";
  let key = "risk.badge.dry_run";
  if (opts.paused) key = "risk.badge.paused";
  else if (!opts.dryRun && opts.canTrade) key = "risk.badge.live";
  else if (!opts.dryRun) key = "risk.badge.live_blocked";
  badge.textContent = t(key);
  badge.dataset.mode = opts.paused ? "paused" : opts.dryRun ? "dry" : "live";
  return badge;
}
