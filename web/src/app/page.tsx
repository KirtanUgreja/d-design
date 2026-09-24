import { headers } from 'next/headers';
import { redirect } from 'next/navigation';

import { listKitsForUser } from '../features/brand-kit/brand-kit.data.js';
import { getEntitlement } from '../features/publish/index.js';
import { auth } from '../lib/auth.js';
import EditorClient from './editor-client.js';

// The editor is session-gated and hits the database; it is never statically
// prerendered (a build must not need a live DB or a session).
export const dynamic = 'force-dynamic';

/**
 * The editor route — gated by a real session (v3, phase 16).
 *
 * The session check is a server-side redirect (an optimization); the data
 * layer is where authorization actually lives (security doc: "authorization
 * is checked at the data layer, never in middleware alone"). The editor is a
 * client component; loading/saving a deck goes through as_user/asUser. The
 * user's team brand kits are fetched here (server-side, through api) and
 * passed down — the client never calls api.
 *
 * The brand kit is a PAID feature (v3/spec.md): free accounts get no kits
 * fetched at all — the gate is server-side, at the point of action, and the
 * client never sees paid-only data (infrastructure.md "entitlement checks are
 * server-side").
 */
export default async function HomePage() {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    redirect('/login');
  }

  // The entitlement read decides the brand-kit gate. Fail-closed: an api that
  // cannot be read means free (no paid-only data leaks to a free user).
  const entitlement = await getEntitlement();
  const plan = entitlement.ok ? entitlement.value.plan : 'free';

  let kits: Awaited<ReturnType<typeof listKitsForUser>> = [];
  if (plan === 'paid') {
    try {
      kits = await listKitsForUser();
    } catch {
      // The api may be down in dev; the editor still works without kits.
      kits = [];
    }
  }

  return <EditorClient userId={session.user.id} kits={kits} plan={plan} />;
}
