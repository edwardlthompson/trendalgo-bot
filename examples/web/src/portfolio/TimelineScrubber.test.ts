import { describe, expect, it } from "vitest";
import { createTimelineScrubber } from "./TimelineScrubber";

describe("createTimelineScrubber", () => {
  it("returns null when dates empty", () => {
    expect(createTimelineScrubber([], null, () => undefined)).toBeNull();
  });

  it("renders range when dates exist", () => {
    const el = createTimelineScrubber(["2026-01-01", "2026-01-02"], "2026-01-02", () => undefined);
    expect(el).not.toBeNull();
    expect(el?.dataset.testid).toBe("timeline-scrubber");
  });
});
