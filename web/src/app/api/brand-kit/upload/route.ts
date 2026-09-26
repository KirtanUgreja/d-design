/**
 * Brand-kit upload route (phase 17) — the ingest path.
 *
 * web's own session gate (server-side redirect elsewhere; here the route
 * requires a session), then:
 *   1. forward the file to the worker (the isolated process — it parses
 *      hostile bytes and has nothing to steal);
 *   2. store the verified/re-encoded bytes under a server UUID key (never a
 *      user filename);
 *   3. record the kit through api (which owns the brand_kits tables).
 *
 * The worker's verdict is fail-closed: any rejection means the file never
 * becomes servable.
 */
import { auth } from '../../../../lib/auth.js';
import { isPaid } from '../../../../features/entitlement/index.js';
import { getEntitlement } from '../../../../features/entitlement/entitlement.data.js';
import { getSessionToken } from '../../../../lib/session-token.js';
import { storage } from '../../../../lib/storage.js';
import { headers } from 'next/headers';
import { NextResponse } from 'next/server';

const WORKER_URL = process.env.WORKER_URL ?? 'http://localhost:8080';

export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  // Session gate: this route grants servable presence, so it fails closed.
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  // The paid gate, at the point of action. The editor only *reads* kits for a
  // paid account, which left creation open to anyone — a free account could
  // spend worker time and storage on a capability it cannot then use.
  const entitlement = await getEntitlement();
  if (!entitlement.ok) {
    return NextResponse.json(
      { error: entitlement.error.message },
      { status: entitlement.error.status },
    );
  }
  if (!isPaid(entitlement.value)) {
    return NextResponse.json({ error: 'brand kits are a paid feature' }, { status: 403 });
  }

  const form = await req.formData();
  const file = form.get('file');
  const teamId = form.get('teamId');
  const name = form.get('name');
  if (!(file instanceof File) || typeof teamId !== 'string' || typeof name !== 'string') {
    return NextResponse.json({ error: 'file, teamId and name are required' }, { status: 400 });
  }
  if (!name) {
    return NextResponse.json({ error: 'name is required' }, { status: 400 });
  }

  const bytes = Buffer.from(await file.arrayBuffer());
  const claimedType = file.type || 'application/octet-stream';

  // Forward to the worker. It verifies magic bytes, caps, re-encodes/sanitizes.
  // An unreachable worker is a refusal, not a crash: it is the component that
  // decides what a valid image is, so with it down nothing may be accepted.
  let workerRes: Response;
  try {
    workerRes = await fetch(`${WORKER_URL}/process`, {
      method: 'POST',
      headers: { 'content-type': claimedType },
      body: bytes as unknown as BodyInit,
    });
  } catch {
    return NextResponse.json({ error: 'the upload worker is unreachable' }, { status: 503 });
  }
  if (!workerRes.ok) {
    const err = (await workerRes.json().catch(() => ({}))) as { error?: string };
    return NextResponse.json({ error: err.error ?? 'file rejected' }, { status: 422 });
  }
  const processed = (await workerRes.json()) as {
    contentType: string;
    dominantColor: string | null;
    data: string;
  };

  // Store the safe bytes under a server UUID key.
  const safeBytes = Buffer.from(processed.data, 'base64');
  const logoRef = await storage.put(safeBytes, processed.contentType);

  // Record the kit through api. The session token travels as the bearer —
  // api resolves sessions itself, and without this header every upload was
  // refused after the object had already been stored and then cleaned up
  // again. Same trust chain as publish: one token, no shared secret.
  const colors = processed.dominantColor ? { accent: processed.dominantColor } : {};
  const token = await getSessionToken();
  const apiRes = await fetch(
    `${process.env.DDESIGN_API_URL ?? 'http://localhost:8000'}/brand-kits`,
    {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        ...(token ? { authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ team_id: teamId, name, colors, logo_ref: logoRef, font_ids: [] }),
    },
  );
  if (!apiRes.ok) {
    // The object is stored but the row failed — remove the orphan (fail
    // closed: no dangling servable asset without a kit).
    await storage.delete(logoRef).catch(() => {});
    return NextResponse.json({ error: 'brand kit could not be saved' }, { status: 502 });
  }

  const kit = (await apiRes.json()) as { id: string };
  return NextResponse.json({ kitId: kit.id, logoRef }, { status: 201 });
}
