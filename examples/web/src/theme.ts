import themeMeta from "./theme-meta.json";

export type ThemeMode = "system" | "light" | "dark";

const STORAGE_KEY = "gp-theme";
const ACCENT_KEY = "gp-accent";

export const ACCENT_PRESETS = (themeMeta as { accentPresets?: string[] }).accentPresets ?? [];

let currentMode: ThemeMode = "system";
let mediaQuery: MediaQueryList | null = null;
let mediaListener: ((event: MediaQueryListEvent) => void) | null = null;
const themeListeners = new Set<() => void>();

function notifyThemeListeners(): void {
  themeListeners.forEach((fn) => fn());
}

export function subscribeThemeChange(listener: () => void): () => void {
  themeListeners.add(listener);
  return () => themeListeners.delete(listener);
}

function readStoredMode(): ThemeMode {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored;
  }
  return "system";
}

function resolvedIsDark(): boolean {
  if (currentMode === "dark") {
    return true;
  }
  if (currentMode === "light") {
    return false;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function updateThemeColorMeta(): void {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (!meta) {
    return;
  }
  meta.setAttribute(
    "content",
    resolvedIsDark() ? themeMeta.themeColorDark : themeMeta.themeColorLight,
  );
}

function applyAccentColor(): void {
  const accent = localStorage.getItem(ACCENT_KEY);
  if (accent) {
    document.documentElement.style.setProperty("--gp-color-primary", accent);
  } else {
    document.documentElement.style.removeProperty("--gp-color-primary");
  }
}

function applyDomTheme(): void {
  document.documentElement.dataset.theme = currentMode;
  updateThemeColorMeta();
  applyAccentColor();
}

function detachMediaListener(): void {
  if (mediaQuery && mediaListener) {
    mediaQuery.removeEventListener("change", mediaListener);
  }
  mediaQuery = null;
  mediaListener = null;
}

function attachMediaListener(): void {
  detachMediaListener();
  if (currentMode !== "system") {
    return;
  }
  mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
  mediaListener = () => updateThemeColorMeta();
  mediaQuery.addEventListener("change", mediaListener);
}

export function getThemeMode(): ThemeMode {
  return currentMode;
}

export function setThemeMode(mode: ThemeMode): void {
  currentMode = mode;
  localStorage.setItem(STORAGE_KEY, mode);
  applyDomTheme();
  attachMediaListener();
  notifyThemeListeners();
}

export function cycleThemeMode(): ThemeMode {
  const next: ThemeMode =
    currentMode === "system" ? "light" : currentMode === "light" ? "dark" : "system";
  setThemeMode(next);
  return next;
}

export function getAccentColor(): string {
  return localStorage.getItem(ACCENT_KEY) ?? "";
}

export function setAccentColor(color: string): void {
  if (color) {
    localStorage.setItem(ACCENT_KEY, color);
  } else {
    localStorage.removeItem(ACCENT_KEY);
  }
  applyAccentColor();
  notifyThemeListeners();
}

export function initTheme(): ThemeMode {
  currentMode = readStoredMode();
  applyDomTheme();
  attachMediaListener();
  return currentMode;
}

export function isDarkTheme(): boolean {
  return resolvedIsDark();
}
