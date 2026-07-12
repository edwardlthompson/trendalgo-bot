import { describe, expect, it, vi } from "vitest";
import { confirmRiskAction } from "./RiskPanel";

describe("confirmRiskAction", () => {
  it("returns confirm() result", () => {
    const spy = vi.spyOn(window, "confirm").mockReturnValue(true);
    expect(confirmRiskAction("pause?")).toBe(true);
    expect(spy).toHaveBeenCalledWith("pause?");
    spy.mockReturnValue(false);
    expect(confirmRiskAction("resume?")).toBe(false);
    spy.mockRestore();
  });
});
