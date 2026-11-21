import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const account = (project: string) => ({
  email: project === "mobile" ? "camille@ufaz.az" : "aygun@ufaz.az",
  password: "playground-pass",
});

async function checkAccessibility(page: Page) {
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
}

async function signIn(page: Page, project: string) {
  const credentials = account(project);
  await page.goto("/signin");
  await page.getByRole("textbox", { name: "Email" }).fill(credentials.email);
  await page.getByLabel("Password").fill(credentials.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/$/);
  if (project === "mobile") {
    await page.getByRole("button", { name: "Open menu" }).click();
    await expect(page.getByRole("link", { name: "Profile" })).toBeVisible();
    await page.keyboard.press("Escape");
  } else {
    await expect(page.getByRole("link", { name: "Profile" })).toBeVisible();
  }
}

test("browse the catalogue and search for a resource", async ({ page }) => {
  await page.goto("/resources");
  await expect(page.getByRole("heading", { name: "Resources", exact: true })).toBeVisible();
  await expect(page.locator("main article").first()).toBeVisible();
  await checkAccessibility(page);

  await page.getByRole("button", { name: /Search/ }).click();
  const search = page.getByRole("combobox", { name: "Search" });
  await search.fill("algebra");
  await expect(page.getByRole("option").first()).toBeVisible();
  await checkAccessibility(page);
  await search.press("Enter");
  await expect(page).toHaveURL(/\/(resources|articles|collections|questions)\//);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

test("sign in and vote on another student's resource", async ({ page }, testInfo) => {
  await signIn(page, testInfo.project.name);
  await page.goto("/resources");
  await page.getByRole("button", { name: /Search/ }).click();
  await page.getByRole("combobox", { name: "Search" }).fill("Operating Systems: Three Easy Pieces");
  await expect(page.getByRole("option").first()).toBeVisible();
  await page.getByRole("option").first().click();
  await expect(
    page.getByRole("heading", { name: "Operating Systems: Three Easy Pieces" }),
  ).toBeVisible();
  const upvote = page.locator("main").getByRole("button", { name: "Upvote" }).first();
  const voteResponse = page.waitForResponse(
    (response) => response.url().includes("/vote") && response.request().method() === "PUT",
  );
  await upvote.click();
  const response = await voteResponse;
  expect(response.ok()).toBeTruthy();
  const vote = await response.json();
  await expect(upvote).toHaveAttribute("aria-pressed", String(vote.my_vote === 1));
  await checkAccessibility(page);
});

test("submit a resource for the shelf", async ({ page }, testInfo) => {
  await signIn(page, testInfo.project.name);
  await page.goto("/submit");
  await expect(page.getByRole("heading", { name: "Add to the library" })).toBeVisible();
  await checkAccessibility(page);

  const title = `Playwright study guide ${testInfo.project.name} ${Date.now()}`;
  await page.getByRole("textbox", { name: "Title" }).fill(title);
  await page
    .getByRole("textbox", { name: "What is it, and who is it for?" })
    .fill("A student-made guide for testing the library submission journey.");
  await page
    .getByRole("textbox", { name: "Link 1" })
    .fill("https://example.org/playwright-study-guide");
  await page.getByRole("button", { name: "Submit for the shelf" }).click();

  await expect(page).toHaveURL(/\/resources\/RES-\d+/);
  await expect(page.getByRole("heading", { name: title })).toBeVisible();
  await checkAccessibility(page);
});
