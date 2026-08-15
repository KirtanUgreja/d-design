import { headers } from 'next/headers';
import { redirect } from 'next/navigation';

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
 * client component; loading/saving a deck goes through as_user/asUser.
 */
export default async function HomePage() {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    redirect('/login');
  }

  return <EditorClient userId={session.user.id} />;
}
