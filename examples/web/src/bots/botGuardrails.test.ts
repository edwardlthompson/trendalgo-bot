import { beforeEach, describe, expect, it } from "vitest";
import {
  DEFAULT_BOT_LIMITS,
  checkGuardrailAction,
  canAddBot,
  canEnableBot,
  proximityIssues,
  nextBotLabel,
  syncBotLimits,
  countEnabledBots,
} from "./botGuardrails";
import { formatGuardrailIssue } from "./botLimitsBanner";

describe("botGuardrails", () => {
  it("suggests next bot label", () => {
    expect(nextBotLabel([{ label: "Bot-1" }])).toBe("Bot-2");
  });

  it("blocks when enabled cap reached", () => {
    const bots = Array.from({ length: 50 }, (_, i) => ({
      id: i + 1,
      enabled: true,
      timeframe: "60",
    }));
    const issue = checkGuardrailAction(
      { ...DEFAULT_BOT_LIMITS, enabled_count: 50 },
      bots,
      { enabling: true, botId: 99, timeframe: "60" },
    );
    expect(issue?.key).toBe("blocked_enabled");
    expect(formatGuardrailIssue(issue!)).toMatch(/50/);
  });

  it("blocks 1S when slot taken", () => {
    const bots = [{ id: 1, enabled: true, timeframe: "1S" }];
    const issue = canEnableBot(DEFAULT_BOT_LIMITS, bots, { id: 2, enabled: false, timeframe: "1S" });
    expect(issue?.key).toBe("blocked_1s");
    expect(formatGuardrailIssue(issue!)).toMatch(/3,600/);
  });

  it("allows adding stopped sub-minute bot", () => {
    expect(canAddBot({ ...DEFAULT_BOT_LIMITS, bot_count: 10 }, [])).toBeNull();
  });

  it("syncs counts from dashboard bots when limits payload is stale", () => {
    const bots = [
      { id: 1, enabled: true, timeframe: "60" },
      { id: 2, enabled: true, timeframe: "5S" },
    ];
    const synced = syncBotLimits(DEFAULT_BOT_LIMITS, bots);
    expect(synced.bot_count).toBe(2);
    expect(synced.enabled_count).toBe(2);
    expect(countEnabledBots(bots)).toBe(2);
  });

  it("blocks add when synced bot count hits cap", () => {
    const bots = Array.from({ length: 500 }, (_, i) => ({ id: i + 1, enabled: false }));
    const issue = canAddBot(DEFAULT_BOT_LIMITS, bots);
    expect(issue?.key).toBe("blocked_total");
  });

  it("warns when nearing enabled cap", () => {
    const limits = { ...DEFAULT_BOT_LIMITS, enabled_count: 43, max_enabled_bots: 50 };
    const warnings = proximityIssues(limits, Array.from({ length: 43 }, (_, i) => ({ id: i, enabled: true })));
    expect(warnings.some((w) => w.key === "near_enabled")).toBe(true);
  });
});

describe("botTemplatesStore", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("saves and lists templates", async () => {
    const { saveBotTemplate, listBotTemplates } = await import("./botTemplatesStore");
    saveBotTemplate("My RSI", {
      label: "Bot-1",
      strategy_id: "RSI",
      pair: "BTC/USD",
      exchange: "kraken",
      timeframe: "60",
      equity_mode: "quote",
      equity_input: 500,
      ta_params: { timeperiod: 14 },
    });
    expect(listBotTemplates()).toHaveLength(1);
    expect(listBotTemplates()[0]?.name).toBe("My RSI");
  });
});
