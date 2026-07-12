import { expect, type Page } from "@playwright/test";

/** Primary tabs: Portfolio, Bot, Scanner, Backtest. Everything else is under More. */
const MORE_LABELS = new Set(["Glossary", "Export", "Billing", "Settings", "Debug"]);

export async function openNavView(page: Page, label: string): Promise<void> {
  await expect(page.getByTestId("mobile-nav")).toBeVisible({ timeout: 15_000 });
  if (MORE_LABELS.has(label)) {
    const moreBtn = page.getByTestId("nav-more-btn");
    await expect(moreBtn).toBeVisible({ timeout: 15_000 });
    await moreBtn.click();
    await page.getByRole("menuitem", { name: label, exact: true }).click();
    return;
  }
  await page.getByRole("button", { name: label, exact: true }).click();
}
