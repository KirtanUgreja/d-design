/**
 * Brand-kit api client — web's read/write path to the FastAPI layer (phase 17).
 *
 * api owns the brand_kits tables; web never touches them through Drizzle (the
 * disjoint-table-ownership rule). This module talks to api's HTTP routes.
 * `import 'server-only'` keeps it (and the session token it may carry) off the
 * client bundle.
 */
import 'server-only';

import { API_BASE, type BrandKit, type Team } from './index.js';

/** The api service base URL (the FastAPI app). */
const API_URL = process.env.DDESIGN_API_URL ?? 'http://localhost:8000';

/** Resolve the current user's session token for the api Authorization header.
 * Web owns the auth tables; it reads its own session like api does. */
async function sessionToken(): Promise<string | null> {
  // The Better Auth cookie is set by the client; on the server we read the
  // session table via Drizzle. A null token means no session.
  const { getSessionToken } = await import('../../lib/session-token.js');
  return getSessionToken();
}

async function authHeaders(): Promise<Record<string, string>> {
  const token = await sessionToken();
  return token ? { authorization: `Bearer ${token}` } : {};
}

export async function listTeams(): Promise<Team[]> {
  const res = await fetch(`${API_URL}${API_BASE}/teams`, {
    headers: await authHeaders(),
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`brand-kit teams: ${res.status}`);
  return (await res.json()) as Team[];
}

export async function listKitsForUser(): Promise<BrandKit[]> {
  const teams = await listTeams();
  const kits: BrandKit[] = [];
  for (const team of teams) {
    const res = await fetch(`${API_URL}${API_BASE}/teams/${team.id}/kits`, {
      headers: await authHeaders(),
      cache: 'no-store',
    });
    if (!res.ok) throw new Error(`brand-kit team kits: ${res.status}`);
    kits.push(...((await res.json()) as BrandKit[]));
  }
  return kits;
}

export async function getKit(kitId: string): Promise<BrandKit> {
  const res = await fetch(`${API_URL}${API_BASE}/${kitId}`, {
    headers: await authHeaders(),
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`brand-kit get: ${res.status}`);
  return (await res.json()) as BrandKit;
}

export async function createKit(input: {
  teamId: string;
  name: string;
  colors: Record<string, string>;
  logoRef: string | null;
  fontIds: string[];
}): Promise<BrandKit> {
  const res = await fetch(`${API_URL}${API_BASE}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...(await authHeaders()) },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`brand-kit create: ${res.status}`);
  return (await res.json()) as BrandKit;
}
