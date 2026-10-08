// Phase 30 -> Verify: the flow end to end on a recording, every direct
// interaction under 400 ms, every state reachable, nothing lost at 200% zoom.
import { expect, test, type Page } from "@playwright/test";

const DOHERTY_MS = 400;

/** The app is behind sign-in now (phase 29): an allowed test account, made
 * once and reused. Its own email, so auth.spec's accounts are never touched. */
async function signIn(page: Page) {
  const email = "proto@example.com";
  const password = "prototype-e2e-password";
  const headers = { origin: "http://localhost:3217" };
  // Better Auth rate-limits sign-ins per address; auth.spec has just made several.
  for (let attempt = 0; attempt < 4; attempt++) {
    await page.request.post("/api/auth/sign-up/email", { data: { email, password, name: "Proto" }, headers });
    const res = await page.request.post("/api/auth/sign-in/email", { data: { email, password }, headers });
    if (res.ok()) return;
    expect(res.status(), await res.text()).toBe(429);
    await page.waitForTimeout(11_000);
  }
  throw new Error("could not sign in the e2e account");
}

/** How long a click takes to show its result. */
async function timed(page: Page, act: () => Promise<void>, shows: () => Promise<void>): Promise<number> {
  const t0 = Date.now();
  await act();
  await shows();
  return Date.now() - t0;
}

test("composer to reveal, keyboard and mouse", async ({ page }) => {
  test.setTimeout(180_000); // the recording replays at its real build time (about a minute)
  await signIn(page);
  await page.goto("/");
  await expect(page.getByLabel("What are you presenting?")).toBeFocused();

  const pick = page.getByRole("radio", { name: /Investor update/ });
  const ms = await timed(page, () => pick.click(), () => expect(pick).toHaveAttribute("aria-checked", "true"));
  expect(ms).toBeLessThan(DOHERTY_MS);
  await page.getByRole("button", { name: "Start" }).click();

  await expect(page).toHaveURL(/\/deck\/update-q3\/outline$/);
  await expect(page.getByText("1 of 4")).toBeVisible();
  await page.getByRole("button", { name: "Skip the rest — use what I gave you" }).click();
  await expect(page.getByText("Interview done")).toBeVisible();
  await page.getByRole("button", { name: "Approve outline" }).click();

  // No look to pick: the deck's look is generated for it.
  await expect(page).toHaveURL(/\/watch$/);
  await expect(page.getByRole("heading", { name: /Composing your deck/ })).toBeVisible();
  await page.getByRole("button", { name: "Stop" }).click();
  await expect(page.getByRole("heading", { name: "Stopped" })).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("link", { name: "Open your deck" })).toBeVisible({ timeout: 120_000 });
  await page.getByRole("link", { name: "Open your deck" }).click();

  await expect(page).toHaveURL(/\/edit$/);
  const notes = page.getByRole("tab", { name: "Notes" });
  const tab = await timed(page, () => notes.click(), () => expect(notes).toHaveAttribute("aria-selected", "true"));
  expect(tab).toBeLessThan(DOHERTY_MS);
  await page.getByRole("tab", { name: "Slide" }).click();
  await page.getByLabel("Ask this slide for a change").fill("make the headline red");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Colour and type come from the look");

  await page.getByRole("link", { name: "Export" }).click();
  await expect(page.getByRole("link", { name: /Download to send/ })).toHaveAttribute("download", /\.html$/);
});

test("a proposal is accepted, then undone", async ({ page }) => {
  await page.goto("/deck/update-q3/edit");
  await page.getByRole("navigation", { name: "Slides" }).getByRole("button").nth(1).click();
  await page.getByRole("button", { name: "Different layout" }).click();
  await page.getByRole("button", { name: "Use it" }).click();
  const undo = page.getByRole("button", { name: /^Undo: Different layout on slide 2/ });
  await expect(undo).toBeEnabled();
  await undo.click();
  await expect(page.getByRole("button", { name: /^Redo: Different layout on slide 2/ })).toBeEnabled();
});

test("a WEB claim opens its quoted source", async ({ page }) => {
  await page.goto("/deck/launch-product/outline");
  await page.getByRole("button", { name: /From a cited source/ }).first().click();
  await expect(page.getByRole("dialog").getByRole("link", { name: "open the page" })).toBeVisible();
});

test("every state has copy, and an unknown deck is a 404 page", async ({ page }) => {
  await page.goto("/states");
  await expect(page.getByRole("row")).toHaveCount(13);
  const res = await page.goto("/deck/nope/outline");
  expect(res?.status()).toBe(404);
  await expect(page.getByText("There’s no deck here.")).toBeVisible();
});

test("nothing scrolls sideways at 200% zoom", async ({ page }) => {
  await page.setViewportSize({ width: 720, height: 450 }); // a 1440 screen at 200%
  for (const path of ["/", "/deck/update-q3/outline", "/deck/update-q3/watch", "/deck/update-q3/edit", "/deck/update-q3/done"]) {
    await page.goto(path);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, path).toBeLessThanOrEqual(1);
  }
});

test("a typed brief is a real deck, and says plainly when the deck service is down", async ({ page }) => {
  await signIn(page);
  await page.goto("/");
  // Even a brief that reads like an example builds for real: only a picked chip replays.
  await page.getByLabel("What are you presenting?").fill("make a pitch deck for tesla");
  await page.getByRole("button", { name: "Start" }).click();
  await expect(page).toHaveURL(/\/$/);
  // No API runs in the e2e build, so a new brief cannot start: it says so, in words.
  await expect(page.getByRole("status")).toContainText("can't reach the deck service");
});

test("a brief typed before signing in survives sign-in and starts", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("What are you presenting?").fill("Board deck for a coffee roaster");
  await page.getByRole("button", { name: "Start" }).click();
  await expect(page).toHaveURL(/\/sign-up\?next=%2F$/);
  await page.getByRole("link", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/sign-in/);
  await signIn(page); // the account exists from the tests above; this sets the session
  await page.goto("/");
  // Back on the composer, the waiting brief starts by itself (no API in this
  // build, so it says so) and is still in the box.
  await expect(page.getByLabel("What are you presenting?")).toHaveValue("Board deck for a coffee roaster");
  await expect(page.getByRole("status")).toContainText("can't reach the deck service");
});
