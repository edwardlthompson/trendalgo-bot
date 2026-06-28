import {
  count1sEnabled,
  countSubMinuteEnabled,
  countSubMinuteSaved,
  meterLevel,
  proximityIssues,
  slotsRemaining,
  syncBotLimits,
  type BotLimits,
  type BotLike,
  type GuardrailIssue,
} from "./botGuardrails";
import { bindPanelDialog } from "../panelDialog";
import { t } from "../i18n";

function formatMsg(key: string, vars?: Record<string, string>): string {
  let text = t(`bots.limits.${key}`);
  if (vars) {
    for (const [k, v] of Object.entries(vars)) {
      text = text.replaceAll(`{${k}}`, v);
    }
  }
  return text;
}

function formatGuardrailIssue(issue: GuardrailIssue): string {
  return formatMsg(issue.key, issue.vars);
}

type MeterRow = {
  id: string;
  labelKey: string;
  used: number;
  max: number;
  statsKey: string;
  extraKey?: string;
  extraVars?: Record<string, string>;
};

function createMeterRow(row: MeterRow): HTMLElement {
  const wrap = document.createElement("div");
  wrap.className = "gp-cap-meter";
  wrap.dataset.testid = `cap-meter-${row.id}`;

  const head = document.createElement("div");
  head.className = "gp-cap-meter-head";
  const label = document.createElement("span");
  label.className = "gp-cap-meter-label";
  label.textContent = t(`bots.limits.meter_${row.labelKey}`);
  head.appendChild(label);

  const level = meterLevel(row.used, row.max);
  const remaining = slotsRemaining(row.used, row.max);
  const pct = row.max > 0 ? Math.round((row.used / row.max) * 100) : 0;

  const track = document.createElement("div");
  track.className = "gp-cap-meter-track";
  track.setAttribute("role", "meter");
  track.setAttribute("aria-valuemin", "0");
  track.setAttribute("aria-valuemax", String(row.max));
  track.setAttribute("aria-valuenow", String(row.used));
  track.setAttribute(
    "aria-label",
    formatMsg(`meter_${row.labelKey}_aria`, {
      used: String(row.used),
      max: String(row.max),
      remaining: String(remaining),
    }),
  );

  const fill = document.createElement("div");
  fill.className = `gp-cap-meter-fill gp-cap-${level}`;
  fill.style.width = `${pct}%`;
  track.appendChild(fill);

  const stats = document.createElement("p");
  stats.className = "gp-cap-meter-stats";
  stats.dataset.testid = `cap-meter-stats-${row.id}`;
  stats.textContent = formatMsg(row.statsKey, {
    used: String(row.used),
    max: String(row.max),
    remaining: String(remaining),
  });

  wrap.append(head, track, stats);

  if (row.extraKey && row.extraVars) {
    const extra = document.createElement("p");
    extra.className = "gp-cap-meter-extra";
    extra.textContent = formatMsg(row.extraKey, row.extraVars);
    wrap.appendChild(extra);
  }

  return wrap;
}

function createWhyDialog(): { dialog: HTMLDialogElement; cleanup: () => void } {
  const dialog = document.createElement("dialog");
  dialog.className = "gp-limits-why-dialog";
  dialog.dataset.testid = "limits-why-dialog";

  const panel = document.createElement("div");
  panel.className = "gp-limits-why-panel";

  const title = document.createElement("h2");
  title.className = "gp-panel-title";
  title.textContent = t("bots.limits.why_dialog_title");

  const notPaywall = document.createElement("p");
  notPaywall.className = "gp-limits-not-paywall";
  notPaywall.dataset.testid = "limits-not-paywall";
  notPaywall.textContent = t("bots.limits.why_not_paywall");

  const body = document.createElement("div");
  body.className = "gp-limits-why-body";
  body.innerHTML = `
    <p>${t("bots.limits.why_p1")}</p>
    <ul>
      <li>${t("bots.limits.why_li_ohlcv")}</li>
      <li>${t("bots.limits.why_li_ta")}</li>
      <li>${t("bots.limits.why_li_subminute")}</li>
      <li>${t("bots.limits.why_li_1s")}</li>
      <li>${t("bots.limits.why_li_cache")}</li>
    </ul>
    <p>${t("bots.limits.why_p2")}</p>
  `;

  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.className = "gp-btn-primary";
  closeBtn.textContent = t("bots.limits.why_close");
  closeBtn.addEventListener("click", () => dialog.close());

  panel.append(title, notPaywall, body, closeBtn);
  dialog.appendChild(panel);
  document.body.appendChild(dialog);

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  let unbind = (): void => {};
  dialog.addEventListener("close", () => unbind());

  return {
    dialog,
    cleanup: () => {
      unbind();
      dialog.remove();
    },
  };
}

export function createBotLimitsMeters(
  limits: BotLimits,
  bots: BotLike[],
): { root: HTMLElement; cleanup: () => void } {
  const scoped = syncBotLimits(limits, bots);
  const root = document.createElement("div");
  root.className = "gp-bot-limits-meters";
  root.dataset.testid = "bot-limits-meters";

  const subRunning = countSubMinuteEnabled(bots);
  const subSaved = countSubMinuteSaved(bots);
  const oneSRunning = count1sEnabled(bots);

  const headRow = document.createElement("div");
  headRow.className = "gp-cap-meters-head";
  const headTitle = document.createElement("h3");
  headTitle.className = "gp-cap-meters-title";
  headTitle.textContent = t("bots.limits.meters_title");

  const whyBtn = document.createElement("button");
  whyBtn.type = "button";
  whyBtn.className = "gp-btn-secondary gp-cap-why-btn";
  whyBtn.dataset.testid = "limits-why-btn";
  whyBtn.textContent = t("bots.limits.why_btn");
  whyBtn.title = t("bots.limits.why_btn_hint");

  headRow.append(headTitle, whyBtn);
  root.appendChild(headRow);

  const grid = document.createElement("div");
  grid.className = "gp-cap-meter-grid";

  grid.appendChild(
    createMeterRow({
      id: "saved",
      labelKey: "saved",
      used: scoped.bot_count,
      max: scoped.max_bots_total,
      statsKey: "meter_saved_stats",
    }),
  );

  grid.appendChild(
    createMeterRow({
      id: "running",
      labelKey: "running",
      used: scoped.enabled_count,
      max: scoped.max_enabled_bots,
      statsKey: "meter_running_stats",
      extraKey: "meter_running_note",
      extraVars: { mode: scoped.paper ? t("health.dry_run") : t("health.live") },
    }),
  );

  grid.appendChild(
    createMeterRow({
      id: "subminute",
      labelKey: "subminute",
      used: subRunning,
      max: scoped.max_sub_minute_enabled,
      statsKey: "meter_subminute_stats",
      extraKey: "meter_subminute_extra",
      extraVars: {
        saved: String(subSaved),
        oneSUsed: String(oneSRunning),
        oneSMax: String(scoped.max_1s_enabled),
      },
    }),
  );

  root.appendChild(grid);

  const issues = proximityIssues(scoped, bots);
  if (issues.length) {
    const list = document.createElement("ul");
    list.className = "gp-bot-limits-warnings";
    list.dataset.testid = "bot-limits-warnings";
    for (const issue of issues) {
      const li = document.createElement("li");
      li.className = `gp-limits-${issue.level}`;
      li.textContent = formatGuardrailIssue(issue);
      list.appendChild(li);
    }
    root.appendChild(list);
  }

  const { dialog, cleanup: dialogCleanup } = createWhyDialog();
  whyBtn.addEventListener("click", () => {
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
      const panel = dialog.querySelector(".gp-limits-why-panel") as HTMLElement;
      if (panel) {
        const unbind = bindPanelDialog(panel, () => dialog.close());
        dialog.addEventListener(
          "close",
          () => unbind(),
          { once: true },
        );
      }
    }
  });

  return {
    root,
    cleanup: dialogCleanup,
  };
}
