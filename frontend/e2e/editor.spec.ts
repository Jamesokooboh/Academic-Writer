import { expect, test } from "@playwright/test";

// Requires the real backend running at NEXT_PUBLIC_API_URL (default http://localhost:8000)
// with the seeded admin account (ADMIN_EMAIL/ADMIN_PASSWORD from backend/.env).
// Playwright only manages the frontend dev server (see playwright.config.ts); start the
// backend yourself first: `.venv/Scripts/python -m uvicorn app.main:app --port 8000`.

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "you@example.com";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "change-me";

test("login redirects to the editor, and logout returns to login", async ({ page }) => {
  await page.goto("/login");

  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByLabel("Password").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/editor$/);
  await expect(page.getByLabel(/writing mode/i)).toBeVisible();
  await expect(page.getByLabel(/word count mode/i)).toBeVisible();
  await expect(page.getByLabel(/rewrite strength/i)).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("typing in the document editor updates the live word count", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(ADMIN_EMAIL);
  await page.getByLabel("Password").fill(ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/editor$/);

  const editor = page.getByPlaceholder(/paste or write your academic text here/i);
  await editor.fill("One two three four five.");

  await expect(page.getByText(/^5 words/)).toBeVisible();
});
