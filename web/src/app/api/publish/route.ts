/**
 * Publish route (phase 18) — the session-gated path from the editor to a
 * hosted URL. Calls publishDeck (render → storage → api). Fails closed: a
 * missing session denies before any render or write.
 *
 * The status is the refusal's, not a blanket 502. `publishDeck` returns a
 * `Result`, and each kind maps to the code the caller deserves — an exhausted
 * quota is api's 402, not "bad gateway".
 */
import { auth } from '../../../lib/auth.js';
import { publishDeck, type PublishRefusal } from '../../../features/publish/index.js';
import { DeckSchema } from '../../../schema/generated/Deck.js';
import { headers } from 'next/headers';
import { NextResponse } from 'next/server';
import { z } from 'zod';

export const dynamic = 'force-dynamic';

/** Image data URIs keyed by slide id — what the render service inlines. */
const ImagesSchema = z.record(z.string(), z.string());

/** The HTTP status an expected refusal maps to — api's own codes preserved. */
function statusFor(kind: PublishRefusal['kind']): number {
  switch (kind) {
    case 'quota_exhausted':
      return 402;
    case 'forbidden':
      return 403;
    case 'kill_switch':
    case 'entitlement_unavailable':
      return 503;
    case 'render_failed':
    case 'save_failed':
      return 502;
  }
}

export async function POST(req: Request) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const body = (await req.json().catch(() => ({}))) as {
    deck?: unknown;
    title?: string;
    images?: unknown;
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

  try {
    const result = await publishDeck(parsed.data, body.title, images.data);
    if (!result.ok) {
      return NextResponse.json(
        { error: result.error.message },
        { status: statusFor(result.error.kind) },
      );
    }
    return NextResponse.json({ url: result.value.url, key: result.value.key }, { status: 201 });
  } catch (err) {
    // Anything reaching here is a bug, not a refusal — expected failures are
    // Result branches above. Answer JSON so the editor can always read it.
    return NextResponse.json(
      { error: (err as Error).message ?? 'publish failed' },
      { status: 500 },
    );
  }
}
