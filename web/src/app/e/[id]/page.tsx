// Embed is publish with a different CSP header (docs/v1/plan/05-publish-present-embed.md
// -> "Embed"). Same artifact, same renderer, no second code path — this
// file exists only so `/e/:id` is a distinct route for next.config.ts's
// headers() to target with the embed CSP; the page itself is `/p/[id]`'s.

export { default } from '../../p/[id]/page';
