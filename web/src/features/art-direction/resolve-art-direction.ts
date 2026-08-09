// Id -> the art direction and the motion vocabulary that belong together.
//
// The one place an `Experience.artDirection` string becomes objects. Before
// there were two directions this did not exist and every consumer wrote
// `CINEMATIC_DARK` — `/p/[id]`, `/e/[id]`, the editor canvas, both dev
// harnesses — which is five places that each had to be found and changed. The
// point of the resolver is that the sixth consumer does not.
//
// Motion travels with the direction rather than beside it: a printed page that
// drifts in over 900ms is not a printed page, so the pairing is a design fact
// and not a caller's choice. The reduced-motion swap still happens in the
// wrapper (`features/present`), because that one reads the environment and the
// renderer core may not.

import type { ArtDirection, ArtDirectionId } from './art-direction';
import { CINEMATIC_DARK } from './cinematic-dark';
import { EDITORIAL_LIGHT } from './editorial-light';
import {
  CINEMATIC_MOTION,
  EDITORIAL_MOTION,
  type MotionVocabulary,
} from './motion-vocabulary';

export interface ResolvedArtDirection {
  artDirection: ArtDirection;
  motion: MotionVocabulary;
}

/** Exhaustive by construction: `Record<ArtDirectionId, ...>` means adding an id
 * to the union without adding a row here is a type error, which is the same
 * trick `TypeRoleKey` plays on the type scale. */
const BY_ID: Record<ArtDirectionId, ResolvedArtDirection> = {
  'cinematic-dark': { artDirection: CINEMATIC_DARK, motion: CINEMATIC_MOTION },
  'editorial-light': { artDirection: EDITORIAL_LIGHT, motion: EDITORIAL_MOTION },
};

/** Total, not partial — the argument is a union the schema already validated
 * at entry, so there is no unknown-id case to fail on and no reason to hand
 * the caller a `Result` it would only ever unwrap. */
export function resolveArtDirection(id: ArtDirectionId): ResolvedArtDirection {
  return BY_ID[id];
}

/** The ids, for the dev harnesses that offer all of them. Derived from the
 * table rather than restated, so it cannot fall behind. */
export const ART_DIRECTION_IDS = Object.keys(BY_ID) as ArtDirectionId[];
