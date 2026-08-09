import 'server-only';

// Reading an art direction out of the store. The replacement for v1's
// `Record<ArtDirectionId, ResolvedArtDirection>` code table.
//
// The table made a missing art direction a compile error, which was the right
// trade while art directions were code and had no versions. It cannot survive a
// database read, and `docs/v2/plan/01-ad-format.md` is explicit that pretending
// otherwise is worse than losing it deliberately: this returns a `Result`, an
// unknown `{id, version}` is `not_found`, and the page that asked renders its
// designed empty state rather than an unstyled tree.
//
// `server-only`, and both halves of that matter. It reaches `api` with the
// caller's credentials-free URL, and it is the module a client component must
// never pull in — `structure.md` mandates the marker on every data module, and
// this is one, even though the store it reads is a service rather than a table.
//
// **Both halves of the reference go in the URL.** Asking for an id and taking
// the newest version would make an experience pinned to version 1 restyle
// itself the moment version 2 landed — v2 rule 15's exact failure mode, and it
// would arrive disguised as a convenience.

import type { ArtDirectionRef } from '@/schema';
import { artDirectionRecordSchema } from '@/schema';
import { err, ok, type Result } from '@/lib/result';

import { fromRecord, type ResolvedRecord } from './from-record';

function apiUrl(): string {
  const url = process.env.API_URL;
  if (!url) throw new Error('API_URL is not set');
  return url;
}

/** The art direction an experience points at, as tokens.
 *
 * `no-store`, like every other read of live state in this codebase: a cached
 * art direction is a page rendering with the tokens someone else's request
 * happened to fetch, and the cost of the fetch is one request per server
 * render of an editor page.
 */
export async function loadArtDirection(
  ref: ArtDirectionRef,
): Promise<Result<ResolvedRecord>> {
  const path = `${apiUrl()}/art-directions/${encodeURIComponent(ref.id)}/${String(ref.version)}`;

  let res: Response;
  try {
    res = await fetch(path, { cache: 'no-store' });
  } catch (e) {
    // `api` being unreachable is an expected failure of an external service,
    // not a bug in this process (rule 3). A bare `fetch` throws on a refused
    // connection, which is how the editor route became a 500 the first time it
    // was opened without `api` running.
    return err(
      'upstream_unavailable',
      e instanceof Error ? e.message : 'api unreachable',
    );
  }
  if (!res.ok) {
    return err(
      res.status === 404 ? 'not_found' : 'upstream_unavailable',
      await res.text(),
    );
  }

  // One parse at entry, with the generated validator. `api` is another process,
  // so its output is not trusted merely because we wrote it — and a token file
  // is the input most likely to be waved through, since it arrives from our own
  // service rather than a text field.
  const parsed = artDirectionRecordSchema.safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);

  return fromRecord(parsed.data);
}

/** Every art direction this caller can see, newest version of each — what a
 * picker offers.
 *
 * Records rather than resolved tokens: a picker renders a name and a swatch,
 * and resolving all of them to token objects to show two is work nobody asked
 * for. The caller resolves the one it selects.
 */
export async function listArtDirections(): Promise<
  Result<ReturnType<typeof artDirectionRecordSchema.parse>[]>
> {
  let res: Response;
  try {
    res = await fetch(`${apiUrl()}/art-directions`, { cache: 'no-store' });
  } catch (e) {
    return err(
      'upstream_unavailable',
      e instanceof Error ? e.message : 'api unreachable',
    );
  }
  if (!res.ok) return err('upstream_unavailable', await res.text());

  const parsed = artDirectionRecordSchema.array().safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}
