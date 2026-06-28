import { describe, expect, it } from "vitest";
import { COIN_ALIASES, resolveCoinSymbol } from "./coinAliases";

describe("coinAliases", () => {
  it("maps Kraken XBT to BTC", () => {
    expect(resolveCoinSymbol("XBT")).toBe("BTC");
    expect(COIN_ALIASES.POL).toBe("MATIC");
  });
});
