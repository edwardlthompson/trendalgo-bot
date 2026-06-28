import { describe, expect, it } from "vitest";
import { createHealthWidget } from "./HealthWidget";

describe("createHealthWidget", () => {
  it("renders equity and bot count", () => {
    const el = createHealthWidget({
      equity_usd: 1000,
      drawdown_pct: 0.05,
      open_exposure_usd: 100,
      bot_count: 1,
      can_trade: true,
      dry_run: true,
      paused: false,
    });
    expect(el.dataset.testid).toBe("health-widget");
    expect(el.textContent).toContain("$1,000.00");
    expect(el.textContent).toContain("5.0%");
  });
});
