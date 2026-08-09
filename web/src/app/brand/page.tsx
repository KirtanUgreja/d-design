// The brand screen's route. Resolves every art direction this account can
// publish under and hands them to the screen.
//
// The screen is a client component and art directions are database rows since
// v2 phase 01, so the read happens here — the contrast notice answers "here is
// what happens wherever you publish this", which needs all of them.
//
// A store that cannot be reached does not take the page down. The brand kit is
// still editable and saveable without it; what is lost is the contrast notice,
// and an empty list renders none rather than a broken one. That is the right
// failure for a panel that is advice: rule 10 is about checks that *grant*
// something, and this one only ever warns.

import { fromRecord } from '@/features/art-direction';
import type { ArtDirection } from '@/features/art-direction';
import { listArtDirections } from '@/features/art-direction/server';

import { BrandScreen } from './brand-screen';

export default async function BrandPage() {
  const listed = await listArtDirections();
  const artDirections: ArtDirection[] = listed.ok
    ? listed.value.flatMap((record) => {
        const resolved = fromRecord(record);
        return resolved.ok ? [resolved.value.artDirection] : [];
      })
    : [];

  return <BrandScreen artDirections={artDirections} />;
}
