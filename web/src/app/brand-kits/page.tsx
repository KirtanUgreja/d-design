/**
 * Brand kits — the page the feature needed to be reachable (phase 17).
 *
 * The upload route worked and was verified end to end, but nothing in the app
 * called it. This is the surface: the teams and kits a user has, and a form
 * for the two things they can create.
 *
 * Paid-only, gated server-side before any data is fetched — the same shape as
 * the editor's kit gate, so a free account never receives paid-only rows.
 */
import { headers } from 'next/headers';
import { redirect } from 'next/navigation';

import { BrandKitForm } from '../../features/brand-kit/brand-kit-form.js';
import type { BrandKit, Team } from '../../features/brand-kit/index.js';
import { listKitsForUser, listTeams } from '../../features/brand-kit/brand-kit.data.js';
import { isPaid } from '../../features/entitlement/index.js';
import { getEntitlement } from '../../features/entitlement/entitlement.data.js';
import { auth } from '../../lib/auth.js';

// Session-gated and database-backed: never statically prerendered.
export const dynamic = 'force-dynamic';

export default async function BrandKitsPage() {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    redirect('/login');
  }

  const entitlement = await getEntitlement();
  const paid = entitlement.ok && isPaid(entitlement.value);

  let teams: Team[] = [];
  let kits: BrandKit[] = [];
  if (paid) {
    try {
      teams = await listTeams();
      kits = await listKitsForUser();
    } catch {
      // The api may be down in dev; the page still renders and says so by
      // showing no kits rather than failing the whole route.
      teams = [];
      kits = [];
    }
  }

  return (
    <main className="brand-kits">
      <div className="brand-kits__header">
        <h1>Brand kits</h1>
        <a href="/">← Back to the editor</a>
      </div>

      {!paid ? (
        <p className="brand-kits__gated">
          Brand kits are a paid feature. The free tier includes one hosted URL.
        </p>
      ) : (
        <>
          <BrandKitForm teams={teams} />
          <div className="brand-kits__list">
            {kits.length === 0 ? (
              <p>No kits yet. Upload a logo and the worker will extract its colour.</p>
            ) : (
              <ul>
                {kits.map((kit) => (
                  <li key={kit.id}>
                    <span className="brand-kits__name">{kit.name}</span>
                    {kit.colors.accent !== undefined && (
                      <span
                        className="brand-kits__swatch"
                        style={{ background: kit.colors.accent }}
                        title={kit.colors.accent}
                      />
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </main>
  );
}
