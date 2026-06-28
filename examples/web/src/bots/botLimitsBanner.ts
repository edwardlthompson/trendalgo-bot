import type { GuardrailIssue, BotLimits, BotLike } from "./botGuardrails";
import { createBotLimitsMeters } from "./botLimitsMeters";
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

export function formatGuardrailIssue(issue: GuardrailIssue): string {
  return formatMsg(issue.key, issue.vars);
}

export function showGuardrailNotice(issue: GuardrailIssue): void {
  const title = issue.level === "blocked" ? t("bots.limits.blocked_title") : t("bots.limits.warning_title");
  window.alert(`${title}\n\n${formatGuardrailIssue(issue)}`);
}

export function createBotLimitsBanner(limits: BotLimits, bots: BotLike[]): { root: HTMLElement; cleanup: () => void } {
  const wrap = document.createElement("div");
  wrap.className = "gp-bot-limits-banner";
  wrap.dataset.testid = "bot-limits-banner";

  const meters = createBotLimitsMeters(limits, bots);
  wrap.appendChild(meters.root);

  return { root: wrap, cleanup: meters.cleanup };
}
