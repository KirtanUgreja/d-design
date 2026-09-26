/**
 * The publish action (phase 18) — server-side, session-gated.
 *
 * The deck → the render service (POST /render, the SAME exporter as the CLI)
 * → storage.put (the single-file HTML, byte-identical to the downloadable
 * file) → api records the hosted key against the saved deck.
 *
 * The published URL serves those exact bytes; no origin server, no second
 * implementation. The hosted page inherits the file's CSP (connect-src 'none')
 * because it IS the file.
 *
 * **Publishing requires a saved deck, and spends a hosted URL.** So the order
 * is: save (free) → render → store → publish (spends). A refusal at the last
 * step removes the stored object, because a hosted page with no deck behind it
 * is worse than a failed publish.
 *
 * Every refusal carries the status the caller should see — api's own codes are
 * passed through rather than translated into a vocabulary and back
 * (typescript.md: expected failures return a Result; only bugs throw).
 *
 * On imports: `decks.data.ts` is the decks feature's server-side entry. This
 * module is the composition point for hosting, and publishing a deck cannot
 * avoid needing one; it does not reach into that feature's internals.
 */
import 'server-only';

import type { Images } from '../decks/index.js';
import type { Deck } from '../../schema/generated/Deck.js';
import { err, ok, type Result } from '../../lib/result.js';
import { storage } from '../../lib/storage.js';
import { getSessionToken } from '../../lib/session-token.js';
import { publishSavedDeck, saveDeck } from '../decks/decks.data.js';

const RENDER_URL = process.env.RENDER_URL ?? 'http://localhost:8001';
const API_URL = process.env.DDESIGN_API_URL ?? 'http://localhost:8000';
// The hosted origin: pages.<domain> in prod; locally the MinIO object URL.
const HOSTED_ORIGIN = process.env.HOSTED_ORIGIN ?? 'http://localhost:9000/ddesign-assets';

export type PublishRefusal = {
  /** The HTTP status to answer the browser with. */
  status: number;
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
  /** The saved deck it was published from — the editor keeps this so the next
   * save updates rather than duplicating. */
  experienceId: string;
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
    return err({ status: 503, message: 'entitlement check unavailable' });
  }
  if (!res.ok) {
    return err({ status: 503, message: `entitlement check failed (${res.status})` });
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
  images: Images = {},
  experienceId?: string,
): Promise<Result<Published, PublishRefusal>> {
  // 0. The entitlement pre-check (an affordance — fail fast before rendering
  // and storing a deck api will refuse). The authoritative gate is api's
  // publish route; if api still refuses after this, the orphan cleanup below
  // holds.
  const entitlement = await getEntitlement();
  if (!entitlement.ok) {
    return entitlement;
  }
  const account = entitlement.value;
  if (account.killSwitch) {
    return err({ status: 503, message: 'service paused (kill switch)' });
  }
  if (account.exhausted) {
    return err({
      status: 402,
      message: `free tier includes ${account.limit} hosted URL` + (account.limit === 1 ? '' : 's'),
    });
  }
  // Paid → no badge. The AI disclosure is never touched by this boolean.
  const badge = account.plan === 'free';

  // 1. Render the single-file HTML (the render service — the same exporter).
  // The image assets travel with the deck: without them the exporter emits a
  // placeholder, so a deck full of generated images would publish empty.
  let renderRes: Response;
  try {
    renderRes = await fetch(`${RENDER_URL}/render`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ deck, images, badge }),
    });
  } catch {
    return err({ status: 503, message: 'render service unreachable' });
  }
  if (!renderRes.ok) {
    return err({ status: 502, message: `render failed: ${renderRes.status}` });
  }
  const html = await renderRes.text();

  // 2. Store the HTML under a server UUID key (never a user filename).
  let key: string;
  try {
    key = await storage.put(Buffer.from(html, 'utf8'), 'text/html');
  } catch {
    return err({ status: 502, message: 'storage write failed' });
  }

  // 3. Save the deck. Publishing records the artefact *against a deck*, so the
  // saved copy is refreshed first — what is hosted and what is saved must not
  // drift. Free: the spend is step 4.
  const saved = await saveDeck({ title, deck, images }, experienceId);
  if (!saved.ok) {
    await storage.delete(key).catch(() => {});
    return err({ status: saved.error.status, message: saved.error.message });
  }

  // 4. Spend the hosted URL.
  const published = await publishSavedDeck(saved.value.id, key);
  if (!published.ok) {
    // The object is stored but the record failed — remove it (fail closed: no
    // dangling hosted page without a saved deck).
    await storage.delete(key).catch(() => {});
    return err({ status: published.error.status, message: published.error.message });
  }

  return ok({ url: `${HOSTED_ORIGIN}/${key}`, key, experienceId: saved.value.id });
}
