// The published artifact, served. No database query, no render beyond what
// Next's own page pipeline already does for any page — reads the frozen
// artifact off local disk and hands it to the same renderer the editor will
// use (docs/v1/plan/05-publish-present-embed.md).
//
// No Suspense boundary: the artifact read is fast enough not to need one,
// and a Suspense-streamed boundary's content only appears once a client-
// executed reveal script runs — meaning it never appears at all with JS
// disabled. A single synchronous render is what actually satisfies "readable
// without JavaScript" (see next.config.ts for why Cache Components is off).

import { notFound } from 'next/navigation';

import { fromMotionRecord, fromRecord } from '@/features/art-direction';
import { PresentedExperience } from '@/features/present';
import { readPublishedArtifact } from '@/features/publish';

export default async function PublishedPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const artifact = await readPublishedArtifact(id);
  if (!artifact.ok) notFound();

  // The artifact carries its own art direction *whole* — the tokens, not a
  // reference to them. That is what makes a published page never restyle itself
  // (v2 rule 15) and what keeps this route a disk read: no store lookup, no call
  // to `api`, per view.
  //
  // A record that will not resolve is a 404 rather than an unstyled page. It
  // means the artifact was written by a build that knew a font family or a
  // motion vocabulary this one does not, and serving the scene tree with no
  // tokens would be strictly worse than serving nothing.
  const resolved = fromRecord(artifact.value.artDirection);
  if (!resolved.ok) notFound();
  const { artDirection } = resolved.value;
  // The vocabulary is frozen in the artifact beside the tokens, for the same
  // reason and by the same rule: a published page never restyles itself, and
  // motion is styling. Two records, two axes, one disk read.
  const motion = fromMotionRecord(artifact.value.motionVocabulary);
  return (
    <PresentedExperience
      scenes={artifact.value.scenes}
      artDirection={artDirection}
      motion={motion}
    />
  );
}
