// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest";
import { createSearchablePicker } from "./SearchablePicker";

describe("SearchablePicker", () => {
  it("opens panel on trigger click and selects an item", () => {
    const onChange = vi.fn();
    const mount = document.createElement("div");
    document.body.appendChild(mount);

    const picker = createSearchablePicker({
      testId: "test-picker",
      label: "Pair",
      value: "BTC/USD",
      items: [
        { id: "BTC/USD", label: "BTC/USD" },
        { id: "ETH/USD", label: "ETH/USD" },
      ],
      favoriteKey: "test-pairs",
      onChange,
    });
    mount.appendChild(picker.root);

    const trigger = mount.querySelector("[data-testid='test-picker-trigger']") as HTMLButtonElement;
    const panel = mount.querySelector("[data-testid='test-picker-panel']") as HTMLElement;

    expect(panel.hidden).toBe(true);
    trigger.click();
    expect(panel.hidden).toBe(false);

    const ethBtn = panel.querySelector(".gp-picker-row-btn") as HTMLButtonElement;
    expect(ethBtn?.textContent).toBeTruthy();
    panel.querySelectorAll(".gp-picker-row-btn")[1]?.dispatchEvent(new MouseEvent("click", { bubbles: true }));

    expect(onChange).toHaveBeenCalledWith("ETH/USD");
    expect(picker.getValue()).toBe("ETH/USD");
    expect(panel.hidden).toBe(true);

    picker.cleanup();
    mount.remove();
  });
});
