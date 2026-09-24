/**
 * The publish action (phase 18) — server-side, session-gated.
 *
 * The deck → the render service (POST /render, the SAME exporter as the CLI)
 * → storage.put (the single-file HTML, byte-identical to the downloadable
 * file) → api records the experience with the published key.
 *
 * The published URL serves those exact bytes; no origin server, no second
 * implementation. The hosted page inherits the file's CSP (connect-src 'none')
 * because it IS the file.
 *
 * Every refusal here is an *expected* failure — an exhausted quota, a paused
 * service, a render service that is down — so this module returns `Result` and
 * the route maps the kind to a status. Throwing made api's 402 arrive at the
 * browser as a 502 (typescript.md: expected failures return a Result; only
 * bugs throw).
 */
import 'server-only';

import type { Deck } from '../../schema/generated/Deck.js';
import { err, ok, type Result } from '../../lib/result.js';
import { storage } from '../../lib/storage.js';
import { getSessionToken } from '../../lib/session-token.js';

const RENDER_URL = process.env.RENDER_URL ?? 'http://localhost:8001';
const API_URL = process.env.DDESIGN_API_URL ?? 'http://localhost:8000';
// The hosted origin: pages.<domain> in prod; locally the MinIO object URL.
const HOSTED_ORIGIN = process.env.HOSTED_ORIGIN ?? 'http://localhost:9000/ddesign-assets';

/** Why a publish was refused. The route maps the kind to an HTTP status. */
export type PublishRefusal = {
  kind:
    | 'quota_exhausted'
    | 'kill_switch'
    | 'entitlement_unavailable'
    | 'forbidden'
    | 'render_failed'
    | 'save_failed';
  message: string;
};

export interface Entitlement {
  plan: string;
  used: number;
  limit: number;
  exhausted: boolean;
  killSwitch: boolean;
}

export interface Published {
  url: string;
  key: string;
}

/** The session token for the api Authorization header (web owns the session
 * table; api resolves the same token read-only). */
async function authHeaders(): Promise<Record<string, string>> {
  const token = await getSessionToken();
  return token ? { authorization: `Bearer ${token}` } : {};
}

/** The account's entitlement, from api (the authoritative source; web's read
 * is an affordance, api's spend gate is the control).
 *
 * Fail-closed: an unreachable or unhappy api is a refusal, never a default
 * plan (AGENTS.md rule 10 — a catch returning a permissive default is a
 * vulnerability, not error handling). */
export async function getEntitlement(): Promise<Result<Entitlement, PublishRefusal>> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/entitlements`, {
      headers: await authHeaders(),
      cache: 'no-store',
    });
  } catch {
    return err({ kind: 'entitlement_unavailable', message: 'entitlement check unavailable' });
  }
  if (!res.ok) {
    return err({
      kind: 'entitlement_unavailable',
      message: `entitlement check failed (${res.status})`,
    });
  }
  const data = (await res.json()) as {
    plan: string;
    used: number;
    limit: number;
    exhausted: boolean;
    kill_switch: boolean;
  };
  return ok({
    plan: data.plan,
    used: data.used,
    limit: data.limit,
    exhausted: data.exhausted,
    killSwitch: data.kill_switch,
  });
}

export async function publishDeck(
  deck: Deck,
  title: string,
): Promise<Result<Published, PublishRefusal>> {
  // 0. The entitlement pre-check (an affordance — fail fast before rendering
  // and storing a deck api will refuse). The authoritative gate is api's
  // experience_create; if api still refuses after this, the orphan cleanup
  // below holds.
  const entitlement = await getEntitlement();
  if (!entitlement.ok) {
    return entitlement;
  }
  const account = entitlement.value;
  if (account.killSwitch) {
    return err({ kind: 'kill_switch', message: 'service paused (kill switch)' });
  }
  if (account.exhausted) {
    return err({
      kind: 'quota_exhausted',
      message: `free tier includes ${account.limit} hosted URL` + (account.limit === 1 ? '' : 's'),
    });
  }
  // Paid → no badge. The AI disclosure is never touched by this boolean.
  const badge = account.plan === 'free';

  // 1. Render the single-file HTML (the render service — the same exporter).
  let renderRes: Response;
  try {
    renderRes = await fetch(`${RENDER_URL}/render`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ deck, badge }),
    });
  } catch {
    return err({ kind: 'render_failed', message: 'render service unreachable' });
  }
  if (!renderRes.ok) {
    return err({ kind: 'render_failed', message: `render failed: ${renderRes.status}` });
  }
  const html = await renderRes.text();

  // 2. Store the HTML under a server UUID key (never a user filename).
  let key: string;
  try {
    key = await storage.put(Buffer.from(html, 'utf8'), 'text/html');
  } catch {
    return err({ kind: 'save_failed', message: 'storage write failed' });
  }

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
    // api's detail is the honest message ("free tier includes 1 hosted URL");
    // surface it rather than a generic failure.
    const detail = (await apiRes.json().catch(() => null)) as { detail?: string } | null;
    const message = detail?.detail ?? `experience save failed: ${apiRes.status}`;
    if (apiRes.status === 402) {
      return err({ kind: 'quota_exhausted', message });
    }
    if (apiRes.status === 403) {
      return err({ kind: 'forbidden', message });
    }
    return err({ kind: 'save_failed', message });
  }

  return ok({ url: `${HOSTED_ORIGIN}/${key}`, key });
}
