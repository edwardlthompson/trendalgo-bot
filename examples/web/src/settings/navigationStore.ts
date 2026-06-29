import type { AppView } from "../shell/MobileNav";

const KEY = "trendalgo.navigation.v1";

const VALID_VIEWS: AppView[] = [
  "portfolio",
  "dashboard",
  "glossary",
  "backtest",
  "export",
  "billing",
  "scanner",
  "settings",
  "debug",
];

export type PersistedNavigation = {
  view: AppView;
  selectedBotId: number | null;
};

function defaultNavigation(): PersistedNavigation {
  return { view: "portfolio", selectedBotId: null };
}

function normalizeView(raw: unknown): AppView {
  if (raw === "strategies") return "dashboard";
  if (raw === "risk" || raw === "config") return "portfolio";
  return VALID_VIEWS.includes(raw as AppView) ? (raw as AppView) : "portfolio";
}

export function loadNavigation(): PersistedNavigation {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return defaultNavigation();
    const parsed = JSON.parse(raw) as Partial<PersistedNavigation>;
    const view = normalizeView(parsed.view);
    const selectedBotId =
      view === "dashboard" && typeof parsed.selectedBotId === "number" && parsed.selectedBotId > 0
        ? parsed.selectedBotId
        : null;
    return { view, selectedBotId };
  } catch {
    return defaultNavigation();
  }
}

export function saveNavigation(nav: PersistedNavigation): void {
  const view = normalizeView(nav.view);
  const payload: PersistedNavigation = {
    view,
    selectedBotId: view === "dashboard" ? nav.selectedBotId : null,
  };
  localStorage.setItem(KEY, JSON.stringify(payload));
}
