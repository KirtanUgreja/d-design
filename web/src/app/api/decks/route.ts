/**
 * Decks route — the browser's path to saving and listing decks.
 *
 * `GET` lists summaries (never payloads: a deck with images is megabytes).
 * `POST` creates a draft. Updates live on the `[id]` route. Saving is free —
 * only publishing spends a hosted URL, which is why it is a different route.
 */
import { headers } from 'next/headers';
import { NextResponse } from 'next/server';

import { listDecks, saveDeck } from '../../../features/decks/decks.data.js';
import { SaveDeckSchema } from '../../../features/decks/index.js';
import { auth } from '../../../lib/auth.js';

export const dynamic = 'force-dynamic';

export async function GET() {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const result = await listDecks();
  if (!result.ok) {
    return NextResponse.json({ error: result.error.message }, { status: result.error.status });
  }
  return NextResponse.json(result.value, { status: 200 });
}

export async function POST(req: Request) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  // One parse at the boundary — the browser's body is external input.
  const parsed = SaveDeckSchema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) {
    return NextResponse.json({ error: 'invalid deck' }, { status: 400 });
  }

  const result = await saveDeck(parsed.data);
  if (!result.ok) {
    return NextResponse.json({ error: result.error.message }, { status: result.error.status });
  }
  return NextResponse.json(result.value, { status: 201 });
}
