// Phase 29 (master plan A2, A6): accounts end to end against a real Better Auth
// on the throwaway auth_test database. The Python API is a stub here, and it
// checks the JWT the /api proxy sends exactly as FastAPI will: EdDSA signature
// against the JWKS, issuer, audience, expiry, and the sub/email/name claims.
import { createPublicKey, verify, type JsonWebKey } from "node:crypto";
import { createServer, type IncomingMessage, type Server } from "node:http";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const BASE = "http://localhost:3217"; // playwright.config.ts
const STUB_PORT = 3218; // API_ORIGIN in playwright.config.ts
const OWNER = { name: "Ada Owner", email: "e2e-owner@example.com", password: "a long e2e password" };

interface Claims {
  sub: string;
  email: string;
  name: string;
  iss: string;
  aud: string | string[];
  exp: number;
  iat: number;
}

// ---- the API stub ------------------------------------------------------------

const b64 = (s: string) => Buffer.from(s, "base64url");
let jwks: JsonWebKey[] = [];

async function verifyJwt(token: string): Promise<{ alg: string; claims: Claims } | null> {
  const [h, p, s] = token.split(".");
  if (!h || !p || !s) return null;
  const header = JSON.parse(b64(h).toString()) as { alg: string; kid: string };
  if (header.alg !== "EdDSA") return null; // the allowlist
  if (!jwks.some((k) => k.kid === header.kid)) {
    const res = await fetch(`${BASE}/api/auth/jwks`);
    jwks = ((await res.json()) as { keys: JsonWebKey[] }).keys;
  }
  const jwk = jwks.find((k) => k.kid === header.kid);
  if (!jwk) return null;
  const key = createPublicKey({ key: jwk, format: "jwk" });
  if (!verify(null, Buffer.from(`${h}.${p}`), key, b64(s))) return null;
  const claims = JSON.parse(b64(p).toString()) as Claims;
  if (claims.iss !== BASE || claims.aud !== "d-design-api" || claims.exp * 1000 < Date.now()) return null;
  return { alg: header.alg, claims };
}

interface Profile {
  id: string;
  email: string;
  name: string;
  avatar: unknown;
}

const stub = {
  calls: [] as string[],
  tokens: [] as { alg: string; claims: Claims }[],
  profiles: new Map<string, Profile>(),
};

const body = (req: IncomingMessage): Promise<unknown> =>
  new Promise((resolve) => {
    let raw = "";
    req.on("data", (c: Buffer) => (raw += c.toString()));
    req.on("end", () => resolve(raw ? JSON.parse(raw) : null));
  });

let server: Server | undefined;

test.beforeAll(async () => {
  const stubServer = createServer(async (req, res) => {
    const send = (status: number, data?: unknown) => {
      res.writeHead(status, { "content-type": "application/json" });
      res.end(data === undefined ? "" : JSON.stringify(data));
    };
    const route = `${req.method} ${req.url}`;
    stub.calls.push(route);
    const auth = req.headers.authorization ?? "";
    const ok = auth.startsWith("Bearer ") ? await verifyJwt(auth.slice(7)) : null;
    if (!ok) return send(401, { error: "Bad token." });
    stub.tokens.push(ok);
    const { sub, email, name } = ok.claims;
    const me = stub.profiles.get(sub) ?? { id: sub, email, name, avatar: null };
    stub.profiles.set(sub, me);
    if (route === "GET /api/me") return send(200, me);
    if (route === "PATCH /api/me") {
      const patch = (await body(req)) as { avatar?: unknown; name?: string };
      if (patch.avatar !== undefined) me.avatar = patch.avatar;
      if (typeof patch.name === "string") me.name = patch.name;
      return send(200, me);
    }
    if (route === "DELETE /api/me") {
      stub.profiles.delete(sub);
      return send(204);
    }
    if (route === "GET /api/decks") return send(200, []);
    if (route === "POST /api/echo?x=1") {
      return send(200, { body: await body(req), lastEventId: req.headers["last-event-id"] ?? null, cookie: req.headers.cookie ?? null });
    }
    if (route === "GET /api/decks/s1/events") {
      // Two events 1.5 s apart: the first must reach the browser before the second exists.
      res.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache" });
      res.write('data: {"seq":1}\n\n');
      setTimeout(() => res.end('data: {"seq":2}\n\n'), 1500);
      return;
    }
    return send(404, { error: "Not found." });
  });
  await new Promise<void>((resolve) => stubServer.listen(STUB_PORT, "127.0.0.1", resolve));
  server = stubServer;
});

// A worker whose tests were all skipped never ran beforeAll.
test.afterAll(async () => {
  const running = server;
  if (running) await new Promise<void>((resolve) => running.close(() => resolve()));
});

// ---- helpers -----------------------------------------------------------------

const origin = { origin: BASE };

/** Removes a leftover account from an earlier run, through Better Auth itself. */
async function removeIfPresent(request: APIRequestContext, email: string, password: string) {
  const signIn = await request.post("/api/auth/sign-in/email", { data: { email, password }, headers: origin });
  if (!signIn.ok()) return;
  const del = await request.post("/api/auth/delete-user", { data: { password }, headers: origin });
  expect(del.ok()).toBe(true);
  await request.post("/api/auth/sign-out", { headers: origin });
}

async function avatarSeed(page: Page, scope = page.locator("main")): Promise<string> {
  const avatar = scope.locator("[data-avatar-seed]").first();
  await expect(avatar).toHaveAttribute("data-avatar-seed", /\S/, { timeout: 30_000 });
  await expect(avatar.locator("img")).toHaveAttribute("src", /^data:image\/svg\+xml/, { timeout: 30_000 });
  return (await avatar.getAttribute("data-avatar-seed")) ?? "";
}

// Neon is remote (and may wake from sleep): auth round trips get room.
test.use({ navigationTimeout: 30_000 });
const SLOW = { timeout: 30_000 };

// One engine: the stub and the accounts are shared state.
test.skip(({ browserName }) => browserName !== "chromium", "accounts run once, in Chromium");
test.describe.configure({ mode: "serial" });

test("sign up, the app, the avatar, sign out, sign in, delete", async ({ page }) => {
  test.setTimeout(120_000);
  await removeIfPresent(page.request, OWNER.email, OWNER.password);

  // Signed out, a protected route goes to sign-in with its return path.
  await page.goto("/account");
  await expect(page).toHaveURL(/\/sign-in\?next=%2Faccount$/);

  await page.getByRole("link", { name: "Create an account" }).click();
  await expect(page).toHaveURL(/\/sign-up\?next=%2Faccount$/);
  await page.getByLabel("Name").fill(OWNER.name);
  await page.getByLabel("Email").fill(OWNER.email);
  await page.getByLabel("Password").fill(OWNER.password);
  await page.getByRole("button", { name: "Create account" }).click();

  // Signed in, back where we were going, with a generated avatar.
  await expect(page).toHaveURL(/\/account$/, SLOW);
  await expect(page.getByRole("heading", { name: OWNER.name, level: 1 })).toBeVisible();
  const first = await avatarSeed(page);

  // The API saw a JWT it could verify, with the claims FastAPI will read.
  const seen = stub.tokens.at(-1);
  expect(seen?.alg).toBe("EdDSA");
  expect(seen?.claims).toMatchObject({ iss: BASE, aud: "d-design-api", email: OWNER.email, name: OWNER.name });
  expect(seen?.claims.sub).toMatch(/\S/);
  expect((seen?.claims.exp ?? 0) - (seen?.claims.iat ?? 0)).toBeLessThanOrEqual(300);

  // Shuffle draws a new face and saves it.
  const img = page.locator("main [data-avatar-seed] img").first();
  const before = await img.getAttribute("src");
  await page.getByRole("button", { name: "Shuffle" }).click();
  await expect(page.locator("main [data-avatar-seed]").first()).not.toHaveAttribute("data-avatar-seed", first, SLOW);
  await expect(img).not.toHaveAttribute("src", before ?? "");
  // Scoped: the password section has a status line of its own.
  await expect(page.getByRole("region", { name: "Your details" }).getByRole("status")).toHaveText("Saved", SLOW);
  const shuffled = await avatarSeed(page);
  expect(stub.calls).toContain("PATCH /api/me");

  // Picking a style saves it too.
  await page.getByRole("radio", { name: "Thumbs" }).click();
  await expect(page.locator("main [data-avatar-style]").first()).toHaveAttribute("data-avatar-style", "thumbs", SLOW);

  // Another protected route, through the proxy to the API.
  await page.goto("/decks");
  await expect(page.getByRole("heading", { name: "Your decks" })).toBeVisible();
  await expect(page.getByText("No decks yet")).toBeVisible(SLOW);

  // The proxy passes body, query and the headers the API reads — never the cookie.
  const echo = await page.request.post("/api/echo?x=1", { data: { a: 1 }, headers: { "last-event-id": "7" } });
  expect(await echo.json()).toEqual({ body: { a: 1 }, lastEventId: "7", cookie: null });

  // The event stream is not buffered: the first event arrives while the second is still to come.
  const stream = await page.evaluate(async () => {
    const t0 = performance.now();
    const res = await fetch("/api/decks/s1/events");
    const reader = res.body?.getReader();
    const first = await reader?.read();
    const at = performance.now() - t0;
    const text = new TextDecoder().decode(first?.value);
    while (reader && !(await reader.read()).done);
    return { at, text, total: performance.now() - t0 };
  });
  expect(stream.text).toContain('"seq":1');
  expect(stream.text).not.toContain('"seq":2');
  expect(stream.total - stream.at).toBeGreaterThan(1000);

  // The browser never gets a JWT.
  expect((await page.request.get("/api/auth/token")).status()).toBe(404);
  const session = await page.request.get("/api/auth/get-session");
  expect(session.ok()).toBe(true);
  expect(session.headers()["set-auth-jwt"]).toBeUndefined();

  // Sign out from the header menu.
  await page.getByRole("button", { name: "Your account" }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/sign-in$/, SLOW);
  await page.goto("/decks");
  await expect(page).toHaveURL(/\/sign-in\?next=%2Fdecks$/);

  // No session: the proxy refuses and the API is never called.
  const calls = stub.calls.length;
  const anon = await page.request.get("/api/decks");
  expect(anon.status()).toBe(401);
  expect(await anon.json()).toEqual({ error: "Sign in to continue." });
  expect(stub.calls.length).toBe(calls);

  // Sign in again: the avatar is the one saved.
  await page.getByLabel("Email").fill(OWNER.email);
  await page.getByLabel("Password").fill(OWNER.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/decks$/, SLOW);
  // The avatar lives in the app bar now, on every page.
  expect(await avatarSeed(page, page.getByRole("banner"))).toBe(shuffled);

  // Delete the account: its decks go first, then the account.
  await page.goto("/account");
  await page.getByRole("button", { name: "Delete account" }).click();
  await page.getByLabel("Your password").fill(OWNER.password);
  await page.getByRole("alertdialog").getByRole("button", { name: "Delete account" }).click();
  await expect(page).toHaveURL(/\/sign-up$/, SLOW);
  expect(stub.calls).toContain("DELETE /api/me");
  const again = await page.request.post("/api/auth/sign-in/email", {
    data: { email: OWNER.email, password: OWNER.password },
    headers: origin,
  });
  expect(again.ok()).toBe(false);
});

test("sign-up is refused for an email not on the list", async ({ page }) => {
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill("stranger@example.com");
  await page.getByLabel("Password").fill("a long stranger password");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.locator("[data-slot=alert]")).toContainText("isn't on the list", SLOW);
  await expect(page).toHaveURL(/\/sign-up$/, SLOW);

  // Server-side, so skipping the form changes nothing.
  const direct = await page.request.post("/api/auth/sign-up/email", {
    data: { email: "stranger@example.com", password: "a long stranger password", name: "S" },
    headers: origin,
  });
  expect(direct.status()).toBe(403);
});

test("the list is case-insensitive and trimmed", async ({ request }) => {
  const second = { email: "second@example.com", password: "another long password" };
  await removeIfPresent(request, second.email, second.password);
  const res = await request.post("/api/auth/sign-up/email", {
    data: { email: "SECOND@example.COM", password: second.password, name: "Second" },
    headers: origin,
  });
  expect(res.ok()).toBe(true);
  await removeIfPresent(request, second.email, second.password);
});
