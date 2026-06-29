import { APP_VERSION } from "../about/aboutSession";
import { createAboutPanel, type AboutPanelState } from "../components/AboutPanel";
import { createSettingsPanel, type SettingsPanelCallbacks } from "../components/SettingsPanel";
import { t } from "../i18n";

export type SettingsViewState = Omit<AboutPanelState, "version"> & { version?: string };

export type SettingsViewCallbacks = SettingsPanelCallbacks & {
  onApplyUpdate?: () => void;
};

export function createSettingsView(
  state: SettingsViewState,
  callbacks: SettingsViewCallbacks,
): HTMLElement {
  const root = document.createElement("div");
  root.className = "gp-settings-view";
  root.dataset.testid = "settings-view";

  const heading = document.createElement("h2");
  heading.className = "gp-panel-title";
  heading.textContent = t("settings.title");
  root.appendChild(heading);

  root.appendChild(
    createSettingsPanel({
      embedded: true,
      onUpdateCheckChange: callbacks.onUpdateCheckChange,
      onDisplayCurrencyChange: callbacks.onDisplayCurrencyChange,
    }),
  );

  const aboutHeading = document.createElement("h3");
  aboutHeading.className = "gp-settings-section-title";
  aboutHeading.textContent = t("about.title");
  root.appendChild(aboutHeading);

  root.appendChild(
    createAboutPanel(
      { ...state, version: state.version || APP_VERSION },
      undefined,
      callbacks.onApplyUpdate,
      { embedded: true },
    ),
  );

  return root;
}
