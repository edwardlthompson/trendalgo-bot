import { test, expect } from "@playwright/test";
import { mockTrendAlgoApi } from "./apiMock";

test.beforeEach(async ({ page }) => {
  await mockTrendAlgoApi(page);
});

test("creates a new empty bot from dashboard toolbar", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("status")).toContainText("API connected", { timeout: 15_000 });
  await page.getByRole("button", { name: "Bot" }).click();
  await expect(page.getByTestId("bot-dashboard")).toBeVisible();
  await page.getByTestId("bot-create-new").click();
  await expect(page.getByTestId("bot-detail")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("bot-detail-settings")).toBeVisible();
});
