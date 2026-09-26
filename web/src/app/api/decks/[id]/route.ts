/**
 * One deck — loading it back, and updating it in place.
 *
 * `GET` returns the deck *and* its image sidecar, parsed. `PUT` updates a
 * draft; both are free (only publishing spends a hosted URL).
 */
import { headers } from 'next/headers';
import { NextResponse } from 'next/server';

import { getDeck, saveDeck } from '../../../../features/decks/decks.data.js';
import { SaveDeckSchema } from '../../../../features/decks/index.js';
import { auth } from '../../../../lib/auth.js';

export const dynamic = 'force-dynamic';

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const { id } = await ctx.params;
  const result = await getDeck(id);
  if (!result.ok) {
    // A deck owned by someone else is a 404 from api: the policy hides it, and
    // this must not confirm that it exists.
    return NextResponse.json({ error: result.error.message }, { status: result.error.status });
  }
  return NextResponse.json(result.value, { status: 200 });
}

export async function PUT(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const parsed = SaveDeckSchema.safeParse(await req.json().catch(() => null));
  if (!parsed.success) {
    return NextResponse.json({ error: 'invalid deck' }, { status: 400 });
  }

  const { id } = await ctx.params;
  const result = await saveDeck(parsed.data, id);
  if (!result.ok) {
    return NextResponse.json({ error: result.error.message }, { status: result.error.status });
  }
  return NextResponse.json(result.value, { status: 200 });
}
