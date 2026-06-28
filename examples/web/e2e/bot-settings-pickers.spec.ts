import { test, expect } from "@playwright/test";
import { mockTrendAlgoApi } from "./apiMock";

async function openBotDetail(page: import("@playwright/test").Page): Promise<void> {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await page.getByRole("button", { name: "Bot" }).click();
  await page.getByTestId("bot-open-1").click();
  await expect(page.getByTestId("bot-detail-settings")).toBeVisible({ timeout: 10_000 });
}

test.beforeEach(async ({ page }) => {
  await mockTrendAlgoApi(page);
});

test("strategy picker lists 100+ TA indicators", async ({ page }) => {
  await openBotDetail(page);
  await page.getByTestId("bot-strategy-picker-trigger").click();
  const panel = page.getByTestId("bot-strategy-picker-panel");
  await expect(panel).toBeVisible();
  const count = await panel.locator(".gp-picker-row-btn").count();
  expect(count).toBeGreaterThan(100);
});

test("pair picker lists 100+ kraken pairs", async ({ page }) => {
  await openBotDetail(page);
  await page.getByTestId("bot-pair-picker-trigger").click();
  const panel = page.getByTestId("bot-pair-picker-panel");
  await expect(panel).toBeVisible();
  const count = await panel.locator(".gp-picker-row-btn").count();
  expect(count).toBeGreaterThan(100);
});

test("timeframe picker preserves chronological order", async ({ page }) => {
  await openBotDetail(page);
  await page.getByTestId("bot-timeframe-picker-trigger").click();
  const panel = page.getByTestId("bot-timeframe-picker-panel");
  const labels = await panel.locator(".gp-picker-row-btn").allTextContents();
  const firstIdx = labels.findIndex((l) => l.includes("1 second"));
  const hourIdx = labels.findIndex((l) => l.includes("1 hour"));
  expect(firstIdx).toBeGreaterThanOrEqual(0);
  expect(hourIdx).toBeGreaterThan(firstIdx);
});

test("strategy picker opens and selects an item", async ({ page }) => {
  await openBotDetail(page);
  await page.getByTestId("bot-strategy-picker-trigger").click();
  const panel = page.getByTestId("bot-strategy-picker-panel");
  await expect(panel).toBeVisible();
  await expect(panel.getByRole("button", { name: "Relative Strength Index", exact: true })).toBeVisible();
  await panel.getByRole("button", { name: "Relative Strength Index", exact: true }).click();
  await expect(panel).toBeHidden();
  await expect(page.getByTestId("bot-strategy-picker-trigger")).toHaveText("Relative Strength Index");
});

test("pair picker opens, searches, and selects", async ({ page }) => {
  await openBotDetail(page);
  await page.getByTestId("bot-pair-picker-trigger").click();
  const panel = page.getByTestId("bot-pair-picker-panel");
  await expect(panel).toBeVisible();
  await panel.getByTestId("bot-pair-picker-search").fill("ETH");
  await panel.getByRole("button", { name: "ETH/USD", exact: true }).click();
  await expect(page.getByTestId("bot-pair-picker-trigger")).toHaveText("ETH/USD");
});

test("timeframe picker opens and lists intervals", async ({ page }) => {
  await openBotDetail(page);
  await page.getByTestId("bot-timeframe-picker-trigger").click();
  const panel = page.getByTestId("bot-timeframe-picker-panel");
  await expect(panel).toBeVisible();
  await expect(panel.getByRole("button", { name: "1 hour", exact: true })).toBeVisible();
});

test("exchange picker opens without collapsing the page", async ({ page }) => {
  await openBotDetail(page);
  await page.getByTestId("bot-exchange-picker-trigger").click();
  const panel = page.getByTestId("bot-exchange-picker-panel");
  await expect(panel).toBeVisible();
  await expect(panel.getByRole("button", { name: "Kraken", exact: true })).toBeVisible();
});

test("exchange change updates pair list in place", async ({ page }) => {
  await openBotDetail(page);
  await page.getByTestId("bot-exchange-picker-trigger").click();
  await page.getByTestId("bot-exchange-picker-panel").getByRole("button", { name: "Binance.US", exact: true }).click();
  await expect(page.getByTestId("bot-exchange-picker-trigger")).toHaveText("Binance.US");
  await page.getByTestId("bot-pair-picker-trigger").click();
  const pairPanel = page.getByTestId("bot-pair-picker-panel");
  await expect(pairPanel).toBeVisible();
  await expect(pairPanel.getByRole("button", { name: "SOL/USD", exact: true })).toBeVisible();
  await expect(page.getByTestId("bot-detail")).toBeVisible();
});

test("pickers work in paper mode when bot detail API is down", async ({ page }) => {
  await page.route(/\/api\/v1\/bots\/\d+$/, (route) => {
    if (route.request().method() === "GET") {
      void route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"down"}' });
      return;
    }
    void route.continue();
  });
  await openBotDetail(page);
  await page.getByTestId("bot-strategy-picker-trigger").click();
  await expect(page.getByTestId("bot-strategy-picker-panel")).toBeVisible();
  await page.getByTestId("bot-timeframe-picker-trigger").click();
  await expect(page.getByTestId("bot-timeframe-picker-panel")).toBeVisible();
});
