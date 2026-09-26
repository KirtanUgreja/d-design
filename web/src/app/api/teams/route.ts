/**
 * Teams route — creating one.
 *
 * Brand kits are team-scoped, so a kit needs a team and there was no way to
 * make one: the rows could only be inserted by hand in SQL. Without this the
 * brand-kit feature had no reachable path for a new account.
 */
import { headers } from 'next/headers';
import { NextResponse } from 'next/server';

import { createTeam } from '../../../features/brand-kit/brand-kit.data.js';
import { auth } from '../../../lib/auth.js';

export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const body = (await req.json().catch(() => ({}))) as { name?: unknown };
  if (typeof body.name !== 'string' || body.name.trim() === '' || body.name.length > 120) {
    return NextResponse.json({ error: 'a team name is required' }, { status: 400 });
  }

  try {
    return NextResponse.json(await createTeam(body.name), { status: 201 });
  } catch (err) {
    return NextResponse.json(
      { error: (err as Error).message ?? 'could not create the team' },
      { status: 502 },
    );
  }
}
