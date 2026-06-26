export function createTooltipHelp(text: string): HTMLElement {
  const span = document.createElement("span");
  span.className = "gp-tooltip-help";
  span.dataset.testid = "tooltip-help";
  span.setAttribute("tabindex", "0");
  span.setAttribute("aria-label", text);
  span.textContent = "?";
  const tip = document.createElement("span");
  tip.className = "gp-tooltip-text";
  tip.textContent = text;
  span.appendChild(tip);
  return span;
}
