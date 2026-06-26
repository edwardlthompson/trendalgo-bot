import { t } from "../i18n";
import type { ThemeMode } from "../theme";
import {
  ACCENT_PRESETS,
  getAccentColor,
  setAccentColor,
} from "../theme";
import {
  applySettingsThemeMode,
  getSettingsThemeMode,
  isUpdateCheckEnabled,
  setUpdateCheckEnabled,
} from "../settings/preferences";

export type SettingsPanelCallbacks = {
  onClose: () => void;
  onUpdateCheckChange?: (enabled: boolean) => void;
};

export function createSettingsPanel(callbacks: SettingsPanelCallbacks): HTMLElement {
  const panel = document.createElement("section");
  panel.className = "gp-settings-panel";
  panel.setAttribute("aria-label", t("settings.title"));
  panel.dataset.testid = "settings-panel";

  const themeMode = getSettingsThemeMode();
  const updateEnabled = isUpdateCheckEnabled();

  panel.innerHTML = `
    <header class="gp-settings-header">
      <h2>${t("settings.title")}</h2>
      <button type="button" class="gp-settings-close" aria-label="${t("settings.close")}">×</button>
    </header>
    <label class="gp-settings-field">
      <span>${t("settings.theme.label")}</span>
      <select data-settings-theme>
        <option value="system">${t("settings.theme.mode.system")}</option>
        <option value="light">${t("settings.theme.mode.light")}</option>
        <option value="dark">${t("settings.theme.mode.dark")}</option>
      </select>
    </label>
    <label class="gp-settings-field gp-settings-toggle">
      <input type="checkbox" data-settings-update ${updateEnabled ? "checked" : ""} />
      <span>${t("settings.update_check.label")}</span>
    </label>
    <div class="gp-settings-field">
      <span>${t("settings.accent.label")}</span>
      <div class="gp-accent-row" data-accent-row></div>
    </div>
  `;

  const themeSelect = panel.querySelector<HTMLSelectElement>("[data-settings-theme]");
  if (themeSelect) {
    themeSelect.value = themeMode;
    themeSelect.addEventListener("change", () => {
      applySettingsThemeMode(themeSelect.value as ThemeMode);
    });
  }

  panel.querySelector<HTMLInputElement>("[data-settings-update]")?.addEventListener("change", (e) => {
    const checked = (e.target as HTMLInputElement).checked;
    setUpdateCheckEnabled(checked);
    callbacks.onUpdateCheckChange?.(checked);
  });

  const accentRow = panel.querySelector("[data-accent-row]");
  const currentAccent = getAccentColor();
  if (accentRow) {
    for (const color of ACCENT_PRESETS) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "gp-accent-swatch";
      btn.style.background = color;
      btn.title = color;
      if (color === currentAccent) btn.setAttribute("aria-pressed", "true");
      btn.addEventListener("click", () => setAccentColor(color));
      accentRow.appendChild(btn);
    }
  }

  panel.querySelector(".gp-settings-close")?.addEventListener("click", callbacks.onClose);
  return panel;
}
