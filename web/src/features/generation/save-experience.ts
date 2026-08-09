// The last step of a build, and the one that was missing until the acceptance
// pass: the scenes the stream produced become a stored `Experience`.
//
// It lives in `generation` rather than in `publish` because it is the terminal
// step of *building*, not the first step of publishing — `streamBuild` yields
// scenes, this turns them into the thing that has an id you can open, edit and
// ship. Publishing is a separate, later, deliberate act.
//
// Browser-side, like every other call in the `/new` flow (Intake, Director,
// Build, Edit all talk to `api` directly — docs/techstack/decisions.md). The
// server-only half of the same resource lives in `features/publish`.

import { err, ok, type Result } from '@/lib/result';
import { experienceSchema, type Experience, type Scene } from '@/schema';

function apiUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) throw new Error('NEXT_PUBLIC_API_URL is not set');
  return url;
}

/** Assemble the streamed scenes into an `Experience` and create it.
 *
 * `experienceId` is the same id every `generations` row for this session was
 * written against, proposed rather than assigned — `api` honours it, so the
 * cost log for this build actually joins to the experience it built (see
 * `api/features/publish/publish_data.py`). The response's id is still what the
 * caller should navigate to: the server has the last word.
 *
 * `meta` is sent because `POST /experiences` parses a whole `Experience`, and
 * every field of it is then ignored and replaced by the row's own server-side
 * timestamps. That is a wart in the request shape, not a fact the client
 * believes — hence the comment rather than a plausible-looking value.
 *
 * The failure this actually has to report well is 422: `Experience` re-runs the
 * structural validators over the whole tree (exactly one `hook` and it is
 * first, at least one CTA, at most one Slot), and a build that streamed eight
 * individually-valid scenes can still fail them collectively. That is the
 * correct outcome — an experience with no CTA is not shippable — and the
 * caller needs the message, not a generic "save failed".
 */
export async function saveBuiltExperience(
  experienceId: string,
  built: { title: string; scenes: Scene[]; brandId: string },
): Promise<Result<Experience>> {
  const now = new Date().toISOString();
  const res = await fetch(`${apiUrl()}/experiences`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      id: experienceId,
      title: built.title,
      mode: 'scroll',
      brandId: built.brandId,
      artDirection: 'cinematic-dark',
      scenes: built.scenes,
      meta: { createdAt: now, updatedAt: now, publishedAt: null },
    }),
  });
  if (!res.ok) {
    return err(
      res.status === 422 ? 'invalid_input' : 'upstream_unavailable',
      await res.text(),
    );
  }
  const parsed = experienceSchema.safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}
