import { t } from "../i18n";

export type ScannerOpportunity = {
  rank: number;
  pair: string;
  uniformity: number;
  gain_pct: number;
  volume_score: number;
  entry_signal: boolean;
  sparkline: number[];
};

export type ScannerSnapshot = {
  version: string;
  generated_at: string | null;
  scan_id: number;
  opportunities: ScannerOpportunity[];
};

export type ScannerSettings = {
  interval_minutes: number;
  min_volume_usd: number;
  min_gain_pct: number;
  min_uniformity: number;
  universe_filter: string;
  trendspotter_boost: boolean;
};

export type ScannerPanelCallbacks = {
  onRunScan: () => void;
  onPin: (pair: string) => void;
  onSaveSettings: (settings: ScannerSettings) => void;
};

function sparklineSvg(values: number[]): string {
  if (!values.length) return "";
  const w = 80;
  const h = 24;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1 || 1)) * w;
      const y = h - ((v - min) / span) * h;
      return `${x},${y}`;
    })
    .join(" ");
  return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline fill="none" stroke="currentColor" stroke-width="1.5" points="${pts}" /></svg>`;
}

export function createScannerPanel(
  snapshot: ScannerSnapshot | null,
  settings: ScannerSettings,
  watchlist: string[],
  loading: boolean,
  callbacks: ScannerPanelCallbacks,
): HTMLElement {
  const section = document.createElement("section");
  section.className = "gp-panel";
  section.dataset.testid = "scanner-panel";

  const title = document.createElement("h2");
  title.className = "gp-panel-title";
  title.textContent = t("scanner.title");
  section.appendChild(title);

  const actions = document.createElement("div");
  actions.className = "gp-panel-actions";
  const runBtn = document.createElement("button");
  runBtn.type = "button";
  runBtn.className = "gp-btn-primary";
  runBtn.dataset.testid = "scanner-run";
  runBtn.textContent = loading ? t("scanner.running") : t("scanner.run");
  runBtn.disabled = loading;
  runBtn.addEventListener("click", () => callbacks.onRunScan());
  actions.appendChild(runBtn);
  section.appendChild(actions);

  const settingsForm = document.createElement("form");
  settingsForm.className = "gp-scanner-settings";
  settingsForm.dataset.testid = "scanner-settings";
  settingsForm.innerHTML = `
    <h3>${t("scanner.settings_title")}</h3>
    <label>${t("scanner.interval")}<input type="number" name="interval_minutes" min="5" max="1440" value="${settings.interval_minutes}" /></label>
    <label>${t("scanner.min_volume")}<input type="number" name="min_volume_usd" min="1" value="${settings.min_volume_usd}" /></label>
    <label>${t("scanner.min_gain")}<input type="number" name="min_gain_pct" step="0.01" min="0" value="${settings.min_gain_pct}" /></label>
    <label>${t("scanner.min_uniformity")}<input type="number" name="min_uniformity" step="0.01" min="0" max="1" value="${settings.min_uniformity}" /></label>
    <label>${t("scanner.universe")}<input type="text" name="universe_filter" value="${settings.universe_filter}" /></label>
    <label><input type="checkbox" name="trendspotter_boost" ${settings.trendspotter_boost ? "checked" : ""} /> ${t("scanner.trendspotter_boost")}</label>
    <button type="submit" class="gp-btn-secondary">${t("scanner.save_settings")}</button>
  `;
  settingsForm.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const fd = new FormData(settingsForm);
    callbacks.onSaveSettings({
      interval_minutes: Number(fd.get("interval_minutes")),
      min_volume_usd: Number(fd.get("min_volume_usd")),
      min_gain_pct: Number(fd.get("min_gain_pct")),
      min_uniformity: Number(fd.get("min_uniformity")),
      universe_filter: String(fd.get("universe_filter")),
      trendspotter_boost: fd.get("trendspotter_boost") === "on",
    });
  });
  section.appendChild(settingsForm);

  if (watchlist.length) {
    const pins = document.createElement("p");
    pins.className = "gp-scanner-watchlist";
    pins.dataset.testid = "scanner-watchlist";
    pins.textContent = `${t("scanner.watchlist")}: ${watchlist.join(", ")}`;
    section.appendChild(pins);
  }

  if (!snapshot?.opportunities?.length) {
    const empty = document.createElement("p");
    empty.dataset.testid = "scanner-empty";
    empty.textContent = t("scanner.empty");
    section.appendChild(empty);
    return section;
  }

  const table = document.createElement("table");
  table.className = "gp-scanner-table";
  table.dataset.testid = "scanner-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th>${t("scanner.col.rank")}</th>
        <th>${t("scanner.col.pair")}</th>
        <th>${t("scanner.col.uniformity")}</th>
        <th>${t("scanner.col.gain")}</th>
        <th>${t("scanner.col.sparkline")}</th>
        <th></th>
      </tr>
    </thead>
    <tbody></tbody>
  `;
  const tbody = table.querySelector("tbody")!;
  for (const row of snapshot.opportunities) {
    const tr = document.createElement("tr");
    tr.dataset.testid = `scanner-row-${row.pair}`;
    tr.innerHTML = `
      <td>${row.rank}</td>
      <td>${row.pair}</td>
      <td>${(row.uniformity * 100).toFixed(1)}%</td>
      <td>${(row.gain_pct * 100).toFixed(1)}%</td>
      <td class="gp-sparkline">${sparklineSvg(row.sparkline)}</td>
      <td><button type="button" class="gp-btn-secondary gp-pin-btn" data-pair="${row.pair}">${t("scanner.pin")}</button></td>
    `;
    tbody.appendChild(tr);
  }
  table.querySelectorAll(".gp-pin-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const pair = (btn as HTMLButtonElement).dataset.pair;
      if (pair) callbacks.onPin(pair);
    });
  });
  section.appendChild(table);

  if (snapshot.generated_at) {
    const meta = document.createElement("p");
    meta.className = "gp-scanner-meta";
    meta.textContent = `${t("scanner.generated")}: ${snapshot.generated_at}`;
    section.appendChild(meta);
  }

  return section;
}
