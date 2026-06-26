import { t } from "../i18n";

export function createTimelineScrubber(
  dates: string[],
  selected: string | null,
  onSelect: (date: string) => void,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "timeline-scrubber";
  section.innerHTML = `<h3>${t("portfolio.timeline")}</h3>`;
  const input = document.createElement("input");
  input.type = "range";
  input.min = "0";
  input.max = String(Math.max(dates.length - 1, 0));
  input.value = String(selected ? dates.indexOf(selected) : 0);
  input.className = "gp-timeline-range";
  const label = document.createElement("p");
  label.dataset.testid = "timeline-date";
  const idx = Number(input.value);
  label.textContent = dates[idx] ?? t("portfolio.timeline_empty");
  input.addEventListener("input", () => {
    const i = Number(input.value);
    const date = dates[i];
    if (date) {
      label.textContent = date;
      onSelect(date);
    }
  });
  section.append(input, label);
  return section;
}
