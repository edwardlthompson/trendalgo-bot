import { describe, expect, it, vi, beforeEach } from "vitest";
import { fetchDashboard } from "./client";

describe("api client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetchDashboard parses response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              dry_run: true,
              equity_usd: 1000,
              open_trades: [],
              open_orders: [],
              bot_count: 1,
              strategy_id: "multi-tf-example",
              pair: "BTC/USD",
              risk: { can_trade: true },
            }),
        }),
      ),
    );
    const data = await fetchDashboard();
    expect(data.pair).toBe("BTC/USD");
  });
});
