import { beforeEach, describe, expect, it } from "vitest";
import { createOhlcvWarmupDialog } from "./ohlcvWarmupDialog";

describe("ohlcvWarmupDialog", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
      this.open = true;
    };
    HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
      this.open = false;
    };
  });

  it("renders progress and log lines", () => {
    const dialog = createOhlcvWarmupDialog();
    dialog.update({
      status: "running",
      progress_pct: 40,
      total_series: 2,
      completed_series: 0,
      current_series: "BTC/USD · 60",
      bars_cached: 100,
      bars_downloaded: 50,
      messages: ["Downloading OHLCV for BTC/USD 1h…", "Received batch of 720 candles"],
    });

    expect(document.querySelector('[data-testid="ohlcv-warmup-progress-fill"]')).toBeTruthy();
    const fill = document.querySelector('[data-testid="ohlcv-warmup-progress-fill"]') as HTMLElement;
    expect(fill.style.width).toBe("40%");
    expect(document.querySelector('[data-testid="ohlcv-warmup-log"]')?.textContent).toMatch(/720 candles/);

    dialog.close();
  });
});
