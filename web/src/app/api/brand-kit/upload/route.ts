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
  const workerRes = await fetch(`${WORKER_URL}/process`, {
    method: 'POST',
    headers: { 'content-type': claimedType },
    body: bytes as unknown as BodyInit,
  });
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

  // Record the kit through api.
  const colors = processed.dominantColor ? { accent: processed.dominantColor } : {};
  const apiRes = await fetch(
    `${process.env.DDESIGN_API_URL ?? 'http://localhost:8000'}/brand-kits`,
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ teamId, name, colors, logoRef, fontIds: [] }),
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
