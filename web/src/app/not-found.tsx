// The republish/unpublish requirement from docs/v1/plan/05-publish-present-embed.md:
// "an artifact that has been taken down is a different message from one
// that never existed" — a design this file cannot fully honor. `/p/[id]`
// serves from local disk with no database query, so a missing artifact
// looks identical whether the id never existed or was published and later
// taken down; telling them apart would mean either a DB read on every view
// (the thing this phase's hot-path requirement forbids) or an audit trail
// (a v3 concern). One honest, designed message for "nothing is here right
// now" beats a fabricated distinction — ponytail: revisit if publish grows
// real audit history.
//
// Root-level so it also covers app routes (e.g. a typo'd path), not only
// the published-page family — one designed empty state, not a framework 404.

export default function NotFound() {
  return (
    <main
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.75rem',
        background: '#08090b',
        color: '#f4f4f5',
        fontFamily: 'system-ui, sans-serif',
        textAlign: 'center',
        padding: '2rem',
      }}
    >
      <p style={{ fontSize: '0.8125rem', letterSpacing: '0.08em', opacity: 0.6 }}>
        NOTHING HERE
      </p>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 500, margin: 0 }}>
        This page isn&apos;t available.
      </h1>
      <p style={{ opacity: 0.7, maxWidth: '32rem' }}>
        The link may be mistyped, or the experience it pointed to has been taken down.
      </p>
    </main>
  );
}
