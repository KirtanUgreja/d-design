/**
 * The publish action (phase 18) — server-side, session-gated.
 *
 * The deck → the render service (POST /render, the SAME exporter as the CLI)
 * → storage.put (the single-file HTML, byte-identical to the downloadable
 * file) → api records the experience with the published key.
 *
 * The published URL serves those exact bytes; no origin server, no second
 * implementation. The hosted page inherits the file's CSP (connect-src
 * 'none') because it IS the file.
 */
import 'server-only';

import type { Deck } from '../../schema/generated/Deck.js';
import { storage } from '../../lib/storage.js';
import { getSessionToken } from '../../lib/session-token.js';

const RENDER_URL = process.env.RENDER_URL ?? 'http://localhost:8001';
const API_URL = process.env.DDESIGN_API_URL ?? 'http://localhost:8000';
// The hosted origin: pages.<domain> in prod; locally the MinIO object URL.
const HOSTED_ORIGIN = process.env.HOSTED_ORIGIN ?? 'http://localhost:9000/ddesign-assets';

/** The session token for the api Authorization header (web owns the session
 * table; api resolves the same token read-only). */
async function authHeaders(): Promise<Record<string, string>> {
  const token = await getSessionToken();
  return token ? { authorization: `Bearer ${token}` } : {};
}

/** The account's entitlement, from api (the authoritative source; web's read
 * is an affordance, api's spend gate is the control). */
export async function getEntitlement(): Promise<{
  plan: string;
  used: number;
  limit: number;
  exhausted: boolean;
  killSwitch: boolean;
}> {
  const res = await fetch(`${API_URL}/entitlements`, {
    headers: await authHeaders(),
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`entitlements: ${res.status}`);
  const data = (await res.json()) as {
    plan: string;
    used: number;
    limit: number;
    exhausted: boolean;
    kill_switch: boolean;
  };
  return {
    plan: data.plan,
    used: data.used,
    limit: data.limit,
    exhausted: data.exhausted,
    killSwitch: data.kill_switch,
  };
}

export async function publishDeck(
  deck: Deck,
  title: string,
): Promise<{ url: string; key: string }> {
  // 0. The entitlement pre-check (an affordance — fail fast before rendering
  // and storing a deck api will refuse). The authoritative gate is api's
  // experience_create; if api still refuses after this, the orphan cleanup
  // below holds. Fail-closed: a pre-check that cannot run refuses — never
  // proceed because the entitlement check was unavailable (AGENTS.md rule 10).
  const entitlement = await getEntitlement();
  if (entitlement.killSwitch) {
    throw new Error('service paused (kill switch)');
  }
  if (entitlement.exhausted) {
    throw new Error(`free tier includes ${entitlement.limit} hosted URL`);
  }
  // Paid → no badge. The AI disclosure is never touched by this boolean.
  const badge = entitlement.plan === 'free';

  // 1. Render the single-file HTML (the render service — the same exporter).
  const renderRes = await fetch(`${RENDER_URL}/render`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ deck, badge }),
  });
  if (!renderRes.ok) {
    throw new Error(`render failed: ${renderRes.status}`);
  }
  const html = await renderRes.text();

  // 2. Store the HTML under a server UUID key (never a user filename).
  const key = await storage.put(Buffer.from(html, 'utf8'), 'text/html');

  // 3. Record the experience through api (which owns the experiences table).
  const apiRes = await fetch(`${API_URL}/experiences`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...(await authHeaders()) },
    body: JSON.stringify({ title, deck_json: JSON.stringify(deck), published_key: key }),
  });
  if (!apiRes.ok) {
    // The object is stored but the row failed — remove the orphan (fail
    // closed: no dangling hosted page without a saved deck).
    await storage.delete(key).catch(() => {});
    // api's 402 detail is the honest message ("free tier includes 1 hosted
    // URL"); surface it rather than a generic failure.
    const detail = (await apiRes.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(detail?.detail ?? `experience save failed: ${apiRes.status}`);
  }

  return { url: `${HOSTED_ORIGIN}/${key}`, key };
}
