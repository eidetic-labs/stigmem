import { expect, test } from "@playwright/test";

test("redirects unauthenticated root traffic to login", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login\?redirect=%2F$/);
  await expect(page.getByText("Fact graph curator dashboard")).toBeVisible();
});

test("shows OIDC configuration warning when provider env is absent", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByText("OIDC is not configured on this node.")).toBeVisible();
  await expect(page.getByText("OIDC_ISSUER_URL")).toBeVisible();
});
