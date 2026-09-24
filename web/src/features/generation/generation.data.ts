/**
 * The generation api client — web's server-side path to the pipeline (v3).
 *
 * The pipeline lives in api; this module is the only place web calls it for
 * generation. `import 'server-only'` keeps the session token off the client
 * bundle.
 *
 * Responses are parsed, never cast: api's answer is model output that has
 * crossed a process boundary, so it is external input here however far it has
 * travelled (AGENTS.md rule 2). The Zod schema is the generated one, so the two
 * halves cannot disagree about the shape. Request bodies are parsed at the
 * route, which is web's own boundary — this module trusts its caller.
 */
import 'server-only';

import type { ZodType } from 'zod';

import { BuiltSchema, DeckSchema, OutlineSchema } from './index.js';
import type { Brief, Built, Deck, Outline, Stage } from './index.js';
import { err, ok, type Result } from '../../lib/result.js';
import { getSessionToken } from '../../lib/session-token.js';

/** The api service base URL (the FastAPI app). */
const API_URL = process.env.DDESIGN_API_URL ?? 'http://localhost:8000';

/** Why a stage refused.
 *
 * `upstream` is the model failing after its bounded repair — the pipeline
 * working as designed, not a bug. It earns its own kind because the user's
 * response is "try again", not "fix your input".
 */
export type GenerationRefusal = {
  kind: 'unauthorized' | 'unreachable' | 'upstream';
  message: string;
};

async function call(stage: Stage, payload: unknown): Promise<Result<unknown, GenerationRefusal>> {
  const token = await getSessionToken();
  if (!token) {
    return err({ kind: 'unauthorized', message: 'no session' });
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}/generation/${stage}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: `Bearer ${token}` },
      body: JSON.stringify(payload),
      cache: 'no-store',
    });
  } catch {
    return err({ kind: 'unreachable', message: 'generation service unreachable' });
  }

  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: string } | null;
    return err({
      // 502 is api reporting a model stage that failed after its repair;
      // anything else is the service being unavailable or refusing outright.
      kind: res.status === 502 ? 'upstream' : 'unreachable',
      message: body?.detail ?? `generation failed (${res.status})`,
    });
  }

  return ok(await res.json());
}

/** Validate a stage's response against its schema. */
function parseWith<T>(
  schema: ZodType<T>,
  result: Result<unknown, GenerationRefusal>,
  label: string,
): Result<T, GenerationRefusal> {
  if (!result.ok) {
    return result;
  }
  const parsed = schema.safeParse(result.value);
  if (!parsed.success) {
    return err({ kind: 'upstream', message: `${label} failed schema validation` });
  }
  return ok(parsed.data);
}

/** Stage one: the brief becomes a schema-validated outline, for approval. */
export async function generateInterview(brief: Brief): Promise<Result<Outline, GenerationRefusal>> {
  return parseWith(OutlineSchema, await call('interview', brief), 'outline');
}

/** Stage two: an approved outline becomes a per-slide Deck. */
export async function generateMapping(input: {
  outline: Outline;
  family_id: string | null;
}): Promise<Result<Deck, GenerationRefusal>> {
  return parseWith(DeckSchema, await call('mapping', input), 'deck');
}

/** Stage three: every slide built, plus its image assets. */
export async function generateBuild(deck: Deck): Promise<Result<Built, GenerationRefusal>> {
  return parseWith(BuiltSchema, await call('build', { deck }), 'built deck');
}
