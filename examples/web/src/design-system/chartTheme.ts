/** Chart colors derived from design tokens (T5). */

export type ChartTheme = {
  background: string;
  text: string;
  grid: string;
  line: string;
  profit: string;
  loss: string;
};

function readVar(name: string, fallback: string): string {
  if (typeof document === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

export function chartThemeFromTokens(): ChartTheme {
  return {
    background: readVar("--gp-color-surface", "transparent"),
    text: readVar("--gp-color-on-surface", "currentColor"),
    grid: readVar("--gp-color-outline", "currentColor"),
    line: readVar("--gp-color-primary", "currentColor"),
    profit: readVar("--gp-color-secondary", "currentColor"),
    loss: readVar("--gp-color-error", "currentColor"),
  };
}
