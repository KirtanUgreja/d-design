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

import { resolveArtDirection } from '@/features/art-direction';
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

  // The artifact carries its own art direction, and this is where that stops
  // being decoration and starts being the product: two published pages from the
  // same renderer, told apart by one string.
  const { artDirection, motion } = resolveArtDirection(artifact.value.artDirection);
  return (
    <PresentedExperience
      scenes={artifact.value.scenes}
      artDirection={artDirection}
      motion={motion}
    />
  );
}
