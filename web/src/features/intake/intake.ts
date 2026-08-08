// Intake's client (docs/v1/plan/08-intake.md). Three calls, all
// non-streaming: one step of the interview, and the read/write of the stored
// Brief that makes "the Brief stays visible and editable, permanently" true of
// the record rather than only of the screen.
//
// Runs in the browser, the same as Director's client and for the same reason —
// every one of these is something the user triggers by typing.

import { err, ok, type Result } from '@/lib/result';
import {
  briefSchema,
  interviewStepSchema,
  type Brief,
  type InterviewStep,
} from '@/schema';

function apiUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) throw new Error('NEXT_PUBLIC_API_URL is not set');
  return url;
}

/** Status -> the client's error code.
 *
 * `refused` does not appear, and the reason is worth stating rather than
 * leaving to be rediscovered: the api maps both `refused` and `invalid_input`
 * to 422 (`api/routes/errors.py`), so the status alone cannot tell them apart.
 * What carries the distinction to the user is the message, which is passed
 * through verbatim — "the model declined the request" reads as a refusal and a
 * claims-check failure reads as one. The phase doc's "a refusal surfaces as a
 * refusal" is asserted where the codes still exist, in `api`'s
 * `test_interview.py`. If the UI ever needs to *branch* on it rather than
 * display it, the fix is a code in the api's error body, not a second guess
 * from a status here. */
function codeFor(status: number): 'quota_exceeded' | 'invalid_input' | 'not_found' {
  if (status === 429) return 'quota_exceeded';
  if (status === 404) return 'not_found';
  return 'invalid_input';
}

/** FastAPI wraps an `HTTPException` message in `{"detail": ...}`. Read it if
 * it is there, fall back to the raw body if it is not — a 500 is HTML, and a
 * `JSON.parse` throwing inside an error path would replace a message the user
 * could act on with a crash. */
async function messageOf(res: Response): Promise<string> {
  const body = await res.text();
  try {
    const parsed: unknown = JSON.parse(body);
    if (parsed !== null && typeof parsed === 'object' && 'detail' in parsed) {
      const { detail } = parsed as { detail: unknown };
      if (typeof detail === 'string') return detail;
    }
  } catch {
    // Not JSON. The body itself is the best message available.
  }
  return body;
}

/** One step of the interview: the next question, or the finished Brief.
 *
 * Stateless, matching the route — the caller holds the answers so far and
 * sends them all back each time. There is no interview session on the server
 * to fall out of sync with what the screen is showing. */
export async function advanceInterview(
  experienceId: string,
  input: { prompt: string; answers: Record<string, string> },
): Promise<Result<InterviewStep>> {
  const res = await fetch(`${apiUrl()}/experiences/${experienceId}/intake`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!res.ok) return err(codeFor(res.status), await messageOf(res));

  const parsed = interviewStepSchema.safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}

/** The stored Brief for an experience, or `not_found` before the interview
 * has produced one. */
export async function loadBrief(experienceId: string): Promise<Result<Brief>> {
  const res = await fetch(`${apiUrl()}/experiences/${experienceId}/brief`);
  if (!res.ok) return err(codeFor(res.status), await messageOf(res));

  const parsed = briefSchema.safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}

/** The user's own edit of their own approved claims.
 *
 * Zod-parsed before the request as well as after it, and that is not
 * belt-and-braces: `cta.href`'s scheme allowlist crossed into the generated
 * validator as a `pattern` (docs/coderules/typescript.md), so a pasted
 * `javascript:` URL is rejected here without a round trip, which is the whole
 * reason the editor gets a validator at all. */
export async function saveBrief(
  experienceId: string,
  brief: Brief,
): Promise<Result<Brief>> {
  const valid = briefSchema.safeParse(brief);
  if (!valid.success) return err('invalid_input', valid.error.message);

  const res = await fetch(`${apiUrl()}/experiences/${experienceId}/brief`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(valid.data),
  });
  if (!res.ok) return err(codeFor(res.status), await messageOf(res));

  const parsed = briefSchema.safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}
