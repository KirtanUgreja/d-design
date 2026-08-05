// The Director's client — one call, one response, no stream
// (docs/v1/plan/07-director.md -> "The call"). Unlike Build's SSE client
// (web/src/features/generation), there is nothing to reveal incrementally:
// Director returns exactly one Outline. Runs in the browser, the same as
// Build's client, since both are steps the user triggers from the outline
// screen (Regenerate calls this; Approve calls Build).

import { err, ok, type Result } from '@/lib/result';
import { outlineSchema, type Brief, type Outline } from '@/schema';

function apiUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) throw new Error('NEXT_PUBLIC_API_URL is not set');
  return url;
}

export async function directBrief(
  experienceId: string,
  brief: Brief,
): Promise<Result<Outline>> {
  const res = await fetch(`${apiUrl()}/experiences/${experienceId}/director`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ brief }),
  });
  if (!res.ok) {
    return err(
      res.status === 429 ? 'quota_exceeded' : 'upstream_unavailable',
      await res.text(),
    );
  }
  const parsed = outlineSchema.safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}
