/** Bot capacity guardrails — keep in sync with src/trendalgo/bots/limits.py */

export const MAX_BOTS_TOTAL = 500;
export const MAX_ENABLED_BOTS_PAPER = 50;
export const MAX_ENABLED_BOTS_LIVE = 20;
export const MAX_SUB_MINUTE_ENABLED_PAPER = 3;
export const MAX_SUB_MINUTE_ENABLED_LIVE = 1;
export const MAX_1S_ENABLED = 1;
export const SUB_MINUTE_INTERVALS = new Set(["1S", "5S", "15S", "30S"]);

/** Show a heads-up when usage reaches this fraction of a cap. */
export const NEAR_LIMIT_RATIO = 0.85;

export type BotLimits = {
  max_bots_total: number;
  max_enabled_bots: number;
  max_sub_minute_enabled: number;
  max_1s_enabled: number;
  sub_minute_intervals: string[];
  bot_count: number;
  enabled_count: number;
  paper: boolean;
};

export type BotLike = {
  id: number;
  enabled?: boolean;
  timeframe?: string;
};

export type GuardrailLevel = "ok" | "warning" | "blocked";

/** i18n key under bots.limits.* */
export type GuardrailIssue = {
  level: GuardrailLevel;
  key: string;
  vars?: Record<string, string>;
};

export function isSubMinute(timeframe: string): boolean {
  return SUB_MINUTE_INTERVALS.has(timeframe);
}

export function normalizeTf(raw: string): string {
  const key = raw.trim();
  if (SUB_MINUTE_INTERVALS.has(key)) return key;
  if (key === "1h") return "60";
  if (key === "1d") return "1D";
  return key;
}

export function isBotEnabled(enabled: unknown): boolean {
  return enabled === true || enabled === 1 || enabled === "1" || enabled === "true";
}

export function countEnabledBots(bots: BotLike[]): number {
  return bots.filter((b) => isBotEnabled(b.enabled)).length;
}

/** Overlay live fleet counts from dashboard bots (source of truth in UI). */
export function syncBotLimits(limits: BotLimits, bots: BotLike[], paper?: boolean): BotLimits {
  return {
    ...limits,
    bot_count: bots.length,
    enabled_count: countEnabledBots(bots),
    paper: paper ?? limits.paper,
  };
}

export function countSubMinuteEnabled(bots: BotLike[]): number {
  return bots.filter((b) => isBotEnabled(b.enabled) && isSubMinute(normalizeTf(String(b.timeframe ?? "60")))).length;
}

export function count1sEnabled(bots: BotLike[]): number {
  return bots.filter((b) => isBotEnabled(b.enabled) && normalizeTf(String(b.timeframe ?? "60")) === "1S").length;
}

export function countSubMinuteSaved(bots: BotLike[]): number {
  return bots.filter((b) => isSubMinute(normalizeTf(String(b.timeframe ?? "60")))).length;
}

export function meterFillRatio(used: number, max: number): number {
  if (max <= 0) return 0;
  return Math.min(1, Math.max(0, used / max));
}

export function meterLevel(used: number, max: number): "ok" | "warning" | "full" {
  if (used >= max) return "full";
  if (meterFillRatio(used, max) >= NEAR_LIMIT_RATIO) return "warning";
  return "ok";
}

export function slotsRemaining(used: number, max: number): number {
  return Math.max(0, max - used);
}

function nearCap(current: number, max: number): boolean {
  return max > 0 && current / max >= NEAR_LIMIT_RATIO;
}

/** Dashboard banners when approaching caps (not yet blocked). */
export function proximityIssues(limits: BotLimits, bots: BotLike[]): GuardrailIssue[] {
  const scoped = syncBotLimits(limits, bots);
  const issues: GuardrailIssue[] = [];
  const subCount = countSubMinuteEnabled(bots);
  const oneSCount = count1sEnabled(bots);

  if (nearCap(scoped.bot_count, scoped.max_bots_total)) {
    issues.push({
      level: "warning",
      key: "near_total",
      vars: { count: String(scoped.bot_count), max: String(scoped.max_bots_total) },
    });
  }
  if (nearCap(scoped.enabled_count, scoped.max_enabled_bots)) {
    issues.push({
      level: "warning",
      key: "near_enabled",
      vars: {
        running: String(scoped.enabled_count),
        max: String(scoped.max_enabled_bots),
        mode: scoped.paper ? "paper" : "live",
      },
    });
  }
  if (subCount >= scoped.max_sub_minute_enabled - 1 && subCount < scoped.max_sub_minute_enabled) {
    issues.push({
      level: "warning",
      key: "near_sub_minute",
      vars: { running: String(subCount), max: String(scoped.max_sub_minute_enabled) },
    });
  }
  if (oneSCount >= scoped.max_1s_enabled && scoped.max_1s_enabled > 0) {
    issues.push({ level: "warning", key: "at_1s_cap", vars: { max: String(scoped.max_1s_enabled) } });
  }
  return issues;
}

/** Block an add / enable / save-with-running action. Returns i18n issue or null. */
export function checkGuardrailAction(
  limits: BotLimits,
  bots: BotLike[],
  opts: {
    adding?: boolean;
    enabling?: boolean;
    timeframe?: string;
    botId?: number;
  },
): GuardrailIssue | null {
  const scoped = syncBotLimits(limits, bots);
  const tf = normalizeTf(opts.timeframe ?? "60");
  const others = opts.botId != null ? bots.filter((b) => b.id !== opts.botId) : bots;

  if (opts.adding && scoped.bot_count >= scoped.max_bots_total) {
    return { level: "blocked", key: "blocked_total", vars: { max: String(scoped.max_bots_total) } };
  }

  if (opts.enabling) {
    const running = others.filter((b) => isBotEnabled(b.enabled)).length;
    if (running >= scoped.max_enabled_bots) {
      return {
        level: "blocked",
        key: "blocked_enabled",
        vars: { max: String(scoped.max_enabled_bots), mode: scoped.paper ? "paper" : "live" },
      };
    }

    if (isSubMinute(tf)) {
      const subCount = countSubMinuteEnabled(others);
      if (subCount >= scoped.max_sub_minute_enabled) {
        return {
          level: "blocked",
          key: "blocked_sub_minute",
          vars: { max: String(scoped.max_sub_minute_enabled) },
        };
      }
      if (tf === "1S") {
        const oneS = count1sEnabled(others);
        if (oneS >= scoped.max_1s_enabled) {
          return { level: "blocked", key: "blocked_1s", vars: { max: String(scoped.max_1s_enabled) } };
        }
      }
    }
  }

  return null;
}

export function canEnableBot(limits: BotLimits, bots: BotLike[], bot: BotLike): GuardrailIssue | null {
  if (isBotEnabled(bot.enabled)) return null;
  return checkGuardrailAction(limits, bots, {
    enabling: true,
    timeframe: String(bot.timeframe ?? "60"),
    botId: bot.id,
  });
}

export function canAddBot(limits: BotLimits, bots: BotLike[] = []): GuardrailIssue | null {
  return checkGuardrailAction(limits, bots, { adding: true });
}

export function nextBotLabel(existing: Array<{ label: string }>): string {
  const used = new Set(existing.map((b) => b.label));
  let n = existing.length + 1;
  while (used.has(`Bot-${n}`)) n += 1;
  return `Bot-${n}`;
}

export const DEFAULT_BOT_LIMITS: BotLimits = {
  max_bots_total: MAX_BOTS_TOTAL,
  max_enabled_bots: MAX_ENABLED_BOTS_PAPER,
  max_sub_minute_enabled: MAX_SUB_MINUTE_ENABLED_PAPER,
  max_1s_enabled: MAX_1S_ENABLED,
  sub_minute_intervals: [...SUB_MINUTE_INTERVALS],
  bot_count: 0,
  enabled_count: 0,
  paper: true,
};
