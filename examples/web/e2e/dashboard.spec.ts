import { test, expect } from "@playwright/test";
import { mockTrendAlgoApi } from "./apiMock";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("trendalgo.onboarding.dismissed", "1");
  });
  await mockTrendAlgoApi(page);
});

test("renders portfolio as default landing", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await expect(page.getByTestId("portfolio-panel")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("net-worth")).toContainText("$98,000.00");
});

test("renders dashboard with bot cards", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await page.getByRole("button", { name: "Bot" }).click();
  await expect(page.getByTestId("bot-dashboard")).toBeVisible();
  await expect(page.getByTestId("health-widget")).toHaveCount(0);
  await expect(page.getByTestId("bot-card-1")).toBeVisible();
  await expect(page.getByTestId("bot-pnl-1")).toContainText("Realized");
  await expect(page.getByTestId("bot-pnl-1")).toContainText("42.50");
});

test("opens bot detail in paper mode when bot API fails", async ({ page }) => {
  await page.route(/\/api\/v1\/bots\/\d+$/, (route) => {
    if (route.request().method() === "GET") {
      void route.fulfill({ status: 503, contentType: "application/json", body: '{"detail":"down"}' });
      return;
    }
    void route.continue();
  });
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await page.getByRole("button", { name: "Bot" }).click();
  await page.getByTestId("bot-open-1").click();
  await expect(page.getByTestId("bot-detail")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("bot-detail-paper-note")).toBeVisible();
  await expect(page.getByTestId("bot-detail-chart")).toBeVisible();
});

test("opens bot detail from dashboard card", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await page.getByRole("button", { name: "Bot" }).click();
  await page.getByTestId("bot-open-1").click();
  await expect(page.getByTestId("bot-detail")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("bot-detail-chart")).toBeVisible();
  await page.getByTestId("bot-detail-back").click();
  await expect(page.getByTestId("bot-dashboard")).toBeVisible();
});

test("runs fleet backtest and shows results", async ({ page }) => {
  test.setTimeout(60_000);
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await page.getByRole("button", { name: "Backtest", exact: true }).click();
  const runBtn = page.getByTestId("backtest-run");
  await expect(runBtn).toBeVisible({ timeout: 15_000 });
  await expect(runBtn).toBeEnabled({ timeout: 15_000 });
  await runBtn.click();
  await expect(page.getByTestId("backtest-fleet-top10")).toBeVisible({ timeout: 20_000 });
});
