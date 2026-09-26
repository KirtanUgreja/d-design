/**
 * The decks api client — web's server-side path to the saved-deck routes.
 *
 * api stores `deck_json` and `images_json` as strings; this module is where
 * that wire format is parsed and produced, so nothing above it handles a JSON
 * string. Response payloads are parsed with the generated schema rather than
 * cast — a stored deck is a deck that crossed a process boundary, and the
 * schema is the boundary (AGENTS.md rule 2).
 *
 * A refusal carries the status the caller should see. api already answers with
 * the right one (401, 403, 404, 402), so this module passes it through rather
 * than translating it into a vocabulary of its own and translating back.
 *
 * `import 'server-only'` keeps the session token off the client bundle.
 */
import 'server-only';

import type { ZodType } from 'zod';

import {
  DeckSummarySchema,
  SavedDeckSchema,
  type DeckSummary,
  type Images,
  type SaveDeckInput,
  type SavedDeck,
} from './index.js';
import type { Deck } from '../../schema/generated/Deck.js';
import { err, ok, type Result } from '../../lib/result.js';
import { getSessionToken } from '../../lib/session-token.js';

const API_URL = process.env.DDESIGN_API_URL ?? 'http://localhost:8000';

export type DeckRefusal = {
  /** The HTTP status to answer the browser with. */
  status: number;
  message: string;
};

/** The wire shape api returns — string where the feature has a Deck. */
interface ExperienceWire {
  id: string;
  title: string;
  deck_json: string;
  images_json: string;
  published_key: string | null;
}

async function request(path: string, init?: RequestInit): Promise<Result<unknown, DeckRefusal>> {
  const token = await getSessionToken();
  if (!token) {
    return err({ status: 401, message: 'no session' });
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${token}`,
        ...(init?.headers ?? {}),
      },
      cache: 'no-store',
    });
  } catch {
    return err({ status: 503, message: 'deck service unreachable' });
  }

  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    return err({ status: res.status, message: body?.detail ?? `deck request failed` });
  }
  return ok(await res.json());
}

function parseWith<T>(
  schema: ZodType<T>,
  result: Result<unknown, DeckRefusal>,
  label: string,
): Result<T, DeckRefusal> {
  if (!result.ok) {
    return result;
  }
  const parsed = schema.safeParse(result.value);
  if (!parsed.success) {
    // A stored deck failing its own schema is a server-side integrity problem,
    // not the caller's mistake — 502, not 400.
    return err({ status: 502, message: `${label} failed schema validation` });
  }
  return ok(parsed.data);
}

/** Turn api's stored record into a deck the editor can load. */
function toSavedDeck(wire: ExperienceWire): Result<SavedDeck, DeckRefusal> {
  return parseWith(
    SavedDeckSchema,
    ok({
      id: wire.id,
      title: wire.title,
      deck: JSON.parse(wire.deck_json) as unknown,
      images: JSON.parse(wire.images_json) as unknown,
      published_key: wire.published_key,
    }),
    'saved deck',
  );
}

/** The user's decks, newest first — summaries only. The editor's list does not
 * need the payloads, and a deck carrying images is megabytes. */
export async function listDecks(): Promise<Result<DeckSummary[], DeckRefusal>> {
  const result = await request('/experiences');
  if (!result.ok) {
    return result;
  }
  const wires = result.value as ExperienceWire[];
  return parseWith(
    DeckSummarySchema.array(),
    ok(wires.map((w) => ({ id: w.id, title: w.title, published_key: w.published_key }))),
    'deck list',
  );
}

export async function getDeck(id: string): Promise<Result<SavedDeck, DeckRefusal>> {
  const result = await request(`/experiences/${encodeURIComponent(id)}`);
  if (!result.ok) {
    return result;
  }
  return toSavedDeck(result.value as ExperienceWire);
}

/** Create a draft, or update one when `id` is given. Saving is free: only
 * publishing spends a hosted URL. */
export async function saveDeck(
  input: SaveDeckInput,
  id?: string,
): Promise<Result<DeckSummary, DeckRefusal>> {
  const result = await request(id === undefined ? '/experiences' : `/experiences/${id}`, {
    method: id === undefined ? 'POST' : 'PUT',
    body: JSON.stringify({
      title: input.title,
      deck_json: JSON.stringify(input.deck),
      images_json: JSON.stringify(input.images),
    }),
  });
  if (!result.ok) {
    return result;
  }
  const wire = result.value as ExperienceWire;
  return ok({ id: wire.id, title: wire.title, published_key: wire.published_key });
}

/** Publish a saved deck: api spends the hosted URL and records the key. */
export async function publishSavedDeck(
  id: string,
  publishedKey: string,
): Promise<Result<{ id: string }, DeckRefusal>> {
  const result = await request(`/experiences/${id}/publish`, {
    method: 'POST',
    body: JSON.stringify({ published_key: publishedKey }),
  });
  if (!result.ok) {
    return result;
  }
  return ok({ id: (result.value as ExperienceWire).id });
}

export type { Deck, Images, SavedDeck };
