// The public surface — the server half. Getting an art direction from
// somewhere, as opposed to doing something with one you already have.
//
// Separate from `index.ts` because the two halves have different runtimes, not
// because they have different topics: everything here either carries
// `import 'server-only'` or reads the filesystem, and the renderer — a client
// component — imports the other half. See `index.ts` for the full reasoning.
//
// Two reads, and the distinction between them is load-bearing:
//
//   loadArtDirection   the production path. Reads the store through `api`,
//                      returns a `Result`, fails closed on an unknown
//                      `{id, version}`.
//   seededRecord(s)    the checked-in seed fixture off disk, for the `/dev/*`
//                      harnesses and the tests. **Never a fallback for the
//                      store** — quietly serving these when `api` is
//                      unreachable would publish a stale art direction to a
//                      customer's audience and report success.

export { listArtDirections, loadArtDirection } from './art-direction.data';
export {
  seededArtDirection,
  seededArtDirections,
  seededMotion,
  seededMotionRecord,
  seededMotionRecords,
  seededRecord,
  seededRecords,
} from './seeded-records';
export { listMotionVocabularies, loadMotion } from './motion.data';
