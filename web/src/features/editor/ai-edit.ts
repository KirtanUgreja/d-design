// The element-scoped prompt's client (docs/v1/plan/09-editor.md -> "The Edit
// call"). It returns the same `props` partial the property panel produces, so
// the caller turns it into a `BlockPatch` and applies it through `patch.ts` —
// one shape, two producers, one validation site.
//
// It deliberately does not apply anything itself. A second write path into the
// tree is how the panel and the model start disagreeing about what a valid
// edit is.

import { err, ok, type Result } from '@/lib/result';
import { editResultSchema, type EditResult, type Scene } from '@/schema';

function apiUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) throw new Error('NEXT_PUBLIC_API_URL is not set');
  return url;
}

export async function editBlock(
  experienceId: string,
  input: { scene: Scene; blockId: string; instruction: string },
  signal?: AbortSignal,
): Promise<Result<EditResult>> {
  const res = await fetch(`${apiUrl()}/experiences/${experienceId}/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
    signal,
  });
  if (!res.ok) {
    return err(
      res.status === 429 ? 'quota_exceeded' : 'invalid_input',
      await messageOf(res),
    );
  }
  const parsed = editResultSchema.safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}

async function messageOf(res: Response): Promise<string> {
  const body = await res.text();
  try {
    const parsed: unknown = JSON.parse(body);
    if (parsed !== null && typeof parsed === 'object' && 'detail' in parsed) {
      const { detail } = parsed as { detail: unknown };
      if (typeof detail === 'string') return detail;
    }
  } catch {
    // Not JSON — a 500 is HTML, and throwing inside an error path would
    // replace a message the user could act on with a crash.
  }
  return body;
}
