/**
 * Publish route (phase 18) — the session-gated path from the editor to a
 * hosted URL. Calls publishDeck (save → render → storage → publish). Fails
 * closed: a missing session denies before any render or write.
 *
 * The status is the refusal's, not a blanket 502: an exhausted quota answers
 * 402, a hidden deck 404, a dead render service 503. `publishDeck` returns a
 * `Result` and carries the code, so this route does not have to know which
 * refusal maps to which number.
 */
import { auth } from '../../../lib/auth.js';
import { publishDeck } from '../../../features/publish/index.js';
import { ImagesSchema } from '../../../features/decks/index.js';
import { DeckSchema } from '../../../schema/generated/Deck.js';
import { headers } from 'next/headers';
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const body = (await req.json().catch(() => ({}))) as {
    deck?: unknown;
    title?: string;
    images?: unknown;
    experienceId?: unknown;
  };
  if (typeof body.title !== 'string') {
    return NextResponse.json({ error: 'title is required' }, { status: 400 });
  }
  // One schema parse at the boundary — the deck is external input here.
  const parsed = DeckSchema.safeParse(body.deck);
  if (!parsed.success) {
    return NextResponse.json({ error: 'invalid deck' }, { status: 400 });
  }
  // The image assets, keyed by slide id. Absent is legitimate: a deck with no
  // image blocks has none.
  const images = ImagesSchema.safeParse(body.images ?? {});
  if (!images.success) {
    return NextResponse.json({ error: 'invalid images' }, { status: 400 });
  }
  const experienceId = typeof body.experienceId === 'string' ? body.experienceId : undefined;

  try {
    const result = await publishDeck(parsed.data, body.title, images.data, experienceId);
    if (!result.ok) {
      return NextResponse.json({ error: result.error.message }, { status: result.error.status });
    }
    return NextResponse.json(
      { url: result.value.url, key: result.value.key, experienceId: result.value.experienceId },
      { status: 201 },
    );
  } catch (err) {
    // Anything reaching here is a bug, not a refusal — expected failures are
    // Result branches above. Answer JSON so the editor can always read it.
    return NextResponse.json(
      { error: (err as Error).message ?? 'publish failed' },
      { status: 500 },
    );
  }
}
