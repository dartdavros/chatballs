import { expect, test } from "@playwright/test";

test("application shell responds", async ({ page, baseURL }) => {
  await page.goto(baseURL ?? "/");
  await expect(page.locator("body")).toBeVisible();
});
