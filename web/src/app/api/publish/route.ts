/**
 * Publish route (phase 18) — the session-gated path from the editor to a
 * hosted URL. Calls publishDeck (render → storage → api). Fails closed: a
 * missing session denies before any render or write.
 */
import { auth } from '../../../lib/auth.js';
import { publishDeck } from '../../../features/publish/index.js';
import { DeckSchema } from '../../../schema/generated/Deck.js';
import { headers } from 'next/headers';
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const body = (await req.json().catch(() => ({}))) as { deck?: unknown; title?: string };
  if (typeof body.title !== 'string') {
    return NextResponse.json({ error: 'title is required' }, { status: 400 });
  }
  // One schema parse at the boundary — the deck is external input here.
  const parsed = DeckSchema.safeParse(body.deck);
  if (!parsed.success) {
    return NextResponse.json({ error: 'invalid deck' }, { status: 400 });
  }

  try {
    const { url, key } = await publishDeck(parsed.data, body.title);
    return NextResponse.json({ url, key }, { status: 201 });
  } catch (err) {
    return NextResponse.json(
      { error: (err as Error).message ?? 'publish failed' },
      { status: 502 },
    );
  }
}
