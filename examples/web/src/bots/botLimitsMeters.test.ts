import { beforeEach, describe, expect, it } from "vitest";
import {
  DEFAULT_BOT_LIMITS,
  meterFillRatio,
  meterLevel,
  slotsRemaining,
} from "./botGuardrails";
import { createBotLimitsMeters } from "./botLimitsMeters";

describe("botLimitsMeters helpers", () => {
  it("computes fill ratio capped at 1", () => {
    expect(meterFillRatio(3, 50)).toBeCloseTo(0.06);
    expect(meterFillRatio(60, 50)).toBe(1);
    expect(meterFillRatio(0, 0)).toBe(0);
  });

  it("classifies meter level", () => {
    expect(meterLevel(10, 50)).toBe("ok");
    expect(meterLevel(43, 50)).toBe("warning");
    expect(meterLevel(50, 50)).toBe("full");
  });

  it("reports remaining slots", () => {
    expect(slotsRemaining(3, 50)).toBe(47);
    expect(slotsRemaining(50, 50)).toBe(0);
  });
});

describe("createBotLimitsMeters", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("renders three meters with stats text", () => {
    const limits = { ...DEFAULT_BOT_LIMITS, bot_count: 0, enabled_count: 0 };
    const bots = [
      { id: 1, enabled: true, timeframe: "5S" },
      { id: 2, enabled: true, timeframe: "60" },
    ];
    const { root, cleanup } = createBotLimitsMeters(limits, bots);
    document.body.appendChild(root);

    expect(root.querySelector('[data-testid="cap-meter-saved"]')).toBeTruthy();
    expect(root.querySelector('[data-testid="cap-meter-running"]')).toBeTruthy();
    expect(root.querySelector('[data-testid="cap-meter-subminute"]')).toBeTruthy();

    const savedStats = root.querySelector('[data-testid="cap-meter-stats-saved"]');
    expect(savedStats?.textContent).toMatch(/2 \/ 500/);
    expect(savedStats?.textContent).toMatch(/498 more/);

    const runningStats = root.querySelector('[data-testid="cap-meter-stats-running"]');
    expect(runningStats?.textContent).toMatch(/2 \/ 50 running/);

    cleanup();
  });

  it("opens why dialog with not-paywall copy", () => {
    HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
      this.open = true;
    };
    HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
      this.open = false;
    };

    const { root, cleanup } = createBotLimitsMeters(DEFAULT_BOT_LIMITS, []);
    document.body.appendChild(root);

    const whyBtn = root.querySelector('[data-testid="limits-why-btn"]') as HTMLButtonElement;
    whyBtn.click();

    const dialog = document.querySelector('[data-testid="limits-why-dialog"]');
    expect(dialog).toBeTruthy();
    expect(document.querySelector('[data-testid="limits-not-paywall"]')?.textContent).toMatch(/not a license/i);

    cleanup();
  });
});
