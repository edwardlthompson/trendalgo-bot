import { APP_VERSION } from "../about/aboutSession";
import { createAboutPanel, type AboutPanelState } from "../components/AboutPanel";
import { createSettingsPanel, type SettingsPanelCallbacks } from "../components/SettingsPanel";
import { createConfigForm, type ExitRulesState } from "../config/ConfigForm";
import { createRecommenderPanel, type Recommendation } from "../ai/RecommenderPanel";
import { createCuratedLibraryPanel, type CuratedPreset } from "../ai/CuratedLibraryPanel";
import { createGrowthPanel } from "../growth/GrowthPanel";
import { createRiskPanel } from "../risk/RiskPanel";
import { createGoLiveWizard } from "../onboarding/GoLiveWizard";
import { t } from "../i18n";

export type SettingsViewState = Omit<AboutPanelState, "version"> & {
  version?: string;
  risk?: Record<string, string | number | boolean> | null;
  strategyId?: string | null;
  strategyParams?: Record<string, number>;
  pairs?: string[];
  exitRules?: ExitRulesState | null;
  recommendations?: Recommendation[] | null;
  aiDisclaimer?: string;
  curatedPresets?: CuratedPreset[] | null;
  curatedVersion?: string;
  referralCode?: string;
  leaderboard?: Array<{ pseudonym: string; score_usd: number }> | null;
  showDiscover?: boolean;
  dryRun?: boolean;
};

export type SettingsViewCallbacks = SettingsPanelCallbacks & {
  onApplyUpdate?: () => void;
  onPause?: () => void;
  onResume?: () => void;
  onSaveConfig?: (params: Record<string, number>) => void;
  onSaveExitRules?: (rules: ExitRulesState) => void;
  onDeployStrategy?: (strategyId: string) => void;
  onGrowthOptIn?: () => void;
  onGrowthBoost?: () => void;
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

  if (callbacks.onPause && callbacks.onResume) {
    const riskHeading = document.createElement("h3");
    riskHeading.className = "gp-settings-section-title";
    riskHeading.textContent = t("risk.title");
    root.appendChild(riskHeading);
    root.appendChild(
      createRiskPanel(state.risk ?? null, {
        onPause: callbacks.onPause,
        onResume: callbacks.onResume,
      }),
    );
    root.appendChild(
      createGoLiveWizard({
        dryRun: state.dryRun ?? true,
        hasKeysHint: false,
      }),
    );
  }

  if (callbacks.onSaveConfig) {
    const configHeading = document.createElement("h3");
    configHeading.className = "gp-settings-section-title";
    configHeading.textContent = t("config.title");
    root.appendChild(configHeading);
    root.appendChild(
      createConfigForm(
        state.strategyId ?? null,
        state.strategyParams ?? {},
        state.pairs ?? [],
        {
          onSave: callbacks.onSaveConfig,
          onSaveExitRules: callbacks.onSaveExitRules,
        },
        state.exitRules ?? undefined,
      ),
    );
  }

  if (state.showDiscover !== false) {
    const discoverHeading = document.createElement("h3");
    discoverHeading.className = "gp-settings-section-title";
    discoverHeading.textContent = t("settings.discover");
    root.appendChild(discoverHeading);
    root.appendChild(
      createRecommenderPanel(
        state.recommendations ?? null,
        state.aiDisclaimer ?? t("ai.disclaimer_default"),
        (id) => callbacks.onDeployStrategy?.(id),
      ),
    );
    root.appendChild(
      createCuratedLibraryPanel(
        state.curatedPresets ?? null,
        state.curatedVersion ?? "1",
        (id) => callbacks.onDeployStrategy?.(id),
      ),
    );
    root.appendChild(
      createGrowthPanel(
        state.referralCode ?? "",
        state.leaderboard ?? null,
        () => callbacks.onGrowthOptIn?.(),
        () => callbacks.onGrowthBoost?.(),
      ),
    );
  }

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
