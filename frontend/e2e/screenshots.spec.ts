import { expect, test } from "@playwright/test";

// Run with E2E_SCREENSHOTS=1 against the seeded local playground. Reference images
// are checked in; normal smoke runs should not rewrite them.
test.skip(!process.env.E2E_SCREENSHOTS, "Reference capture is opt-in");

test("capture home, article and profile in both themes", async ({ page, request }, testInfo) => {
  const login = await request.post("/api/auth/login", {
    data: { email: "aygun@ufaz.az", password: "playground-pass" },
  });
  expect(login.ok()).toBeTruthy();
  const { access_token: token, user } = await login.json();

  const articles = await request.get("/api/articles");
  expect(articles.ok()).toBeTruthy();
  const existing = (await articles.json()).items.find(
    (item: { title: string }) => item.title === "A student's field notes from UFAZ",
  );
  let slug: string = existing?.slug;
  if (!slug) {
    const article = await request.post("/api/articles", {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        title: "A student's field notes from UFAZ",
        excerpt: "A short guide to finding useful work in the student library.",
        body_md:
          "## Start with a question\n\nThe best catalogue entry tells another student when a resource is useful and how to begin.\n\n## Leave a trail\n\nAdd context, write down what helped, and share the result with the next cohort.",
        tags: ["campus", "study"],
        publish: true,
      },
    });
    expect(article.ok()).toBeTruthy();
    slug = (await article.json()).slug;
  }

  const screens = [
    { name: "home", path: "/", heading: /./ },
    { name: "article", path: `/articles/${slug}`, heading: /A student's field notes from UFAZ/ },
    { name: "profile", path: `/people/${user.id}`, heading: /Aygün Məmmədova/ },
  ];

  for (const theme of ["light", "dark"] as const) {
    await page.addInitScript((choice) => localStorage.setItem("theme", choice), theme);
    for (const screen of screens) {
      await page.goto(screen.path);
      await expect(page.getByRole("heading", { level: 1, name: screen.heading })).toBeVisible({
        timeout: 15_000,
      });
      await page.evaluate(() => document.fonts.ready);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
        `${screen.name} overflows at ${testInfo.project.name} width in ${theme} theme`,
      ).toBeTruthy();
      await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });
      await page.screenshot({
        path: `e2e/screenshots/${screen.name}-${testInfo.project.name}-${theme}.png`,
        fullPage: true,
        animations: "disabled",
      });
    }
  }
});
