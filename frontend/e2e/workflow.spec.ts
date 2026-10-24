import { test, expect } from "@playwright/test";

test("configure, persist, navigate and queue a real simulation", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Overview", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Architecture Configurator", exact: false })
    .click();
  await page
    .getByLabel("Configuration name", { exact: true })
    .fill(`Browser baseline ${Date.now()}`);
  await page
    .getByRole("button", { name: "Save architecture", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Architecture saved" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Open simulation workspace", exact: false })
    .click();
  await page.getByLabel("Matrix dimension", { exact: true }).fill("2");
  await page
    .getByRole("button", { name: "Run simulation", exact: false })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Simulation queued" }),
  ).toBeVisible();
  for (const name of [
    "Performance Dashboard",
    "Architecture Comparison",
    "Design Space Explorer",
    "Experiment History",
  ]) {
    await page.getByRole("button", { name, exact: false }).click();
    await expect(
      page.getByRole("heading", { name, exact: true }),
    ).toBeVisible();
  }
  await page.getByRole("button", { name: "Overview", exact: false }).click();
  await expect(
    page.getByRole("heading", { name: "Overview", exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
  await page.screenshot({
    path: "../docs/screenshots/overview.png",
    fullPage: true,
  });
});

test("mobile navigation and configuration remain usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .getByRole("button", { name: "Architecture Configurator", exact: false })
    .click();
  await expect(
    page.getByLabel("Configuration name", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Save architecture", exact: true }),
  ).toBeEnabled();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflow).toBe(false);
  await page.screenshot({
    path: "../docs/screenshots/mobile-configurator.png",
    fullPage: true,
  });
});

test("compare real completed runs and inspect a measured sweep", async ({
  page,
  request,
}) => {
  const response = await request.get("/api/simulations?limit=200");
  const runs = await response.json();
  const completed = runs.filter(
    (r: { status: string }) => r.status === "completed",
  );
  const cohort = completed.find(
    (candidate: { benchmark: string; size: number }) =>
      completed.filter(
        (r: { benchmark: string; size: number }) =>
          r.benchmark === candidate.benchmark && r.size === candidate.size,
      ).length >= 2,
  );
  const pair = cohort
    ? completed
        .filter(
          (r: { benchmark: string; size: number }) =>
            r.benchmark === cohort.benchmark && r.size === cohort.size,
        )
        .slice(0, 2)
    : [];
  test.skip(
    pair.length < 2,
    "Requires real measured study runs; synthetic results are prohibited",
  );
  await page.goto("/");
  await page
    .getByRole("button", { name: "Architecture Comparison", exact: false })
    .click();
  for (const run of pair)
    await page.getByLabel(`Compare run ${run.id}`, { exact: true }).check();
  await page
    .getByRole("button", { name: "Compare 2 runs", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: `Differences from ${pair[0].id.slice(0, 8)}`,
    }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/comparison.png",
    fullPage: true,
  });
  const experiments = await (await request.get("/api/experiments")).json();
  if (experiments.length) {
    await page
      .getByRole("button", { name: "Design Space Explorer", exact: false })
      .click();
    await page
      .getByLabel("Experiment", { exact: true })
      .selectOption(experiments[0].id);
    await expect(
      page.getByRole("heading", { name: "Measured IPC heatmap", exact: true }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Compute Pareto frontier", exact: true })
      .click();
    await expect(
      page.getByRole("heading", {
        name: "Feasible Pareto configurations",
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.getByRole("alert")).toHaveCount(0);
    await page.screenshot({
      path: "../docs/screenshots/explorer.png",
      fullPage: true,
    });
  }
});
