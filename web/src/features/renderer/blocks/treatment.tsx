// Making a photograph belong to the art direction.
//
// docs/v2/plan/15-images.md -> "Treatment: the part that makes it look
// art-directed". This is the half that changes the output and the half nobody
// asks for: an untreated stock photo under `cinematic-dark` reads as an image
// pasted onto a dark page rather than part of one.
//
// Everything here is flat colour and blend modes. **Duotone in particular is
// done without a gradient and without an SVG filter**: greyscale the image,
// stack a `multiply` layer in the shadow token and a `screen` layer in the
// highlight token. Two flat colours, two blend modes. It is the classic
// implementation and it is also the only one rule 18 permits — which is why
// phase 14 lands before this one.

import type { ArtDirection, ImageTone, Ratio } from '@/features/art-direction';

import { TextureLayerView } from '../texture/texture-layer';
import { COLOR_VAR, hardShadow, spaceVar } from '../tokens';

/** `filter` is a blur-free use of the property. Rule 19 bans `blur()`, not the
 * property — `grayscale` and `contrast` carry no light. */
const TONE_FILTER: Record<ImageTone, string | undefined> = {
  'as-shot': undefined,
  mono: 'grayscale(1)',
  // Greyscale first: the two colour layers below supply all the hue, so any
  // surviving original colour muddies them.
  duotone: 'grayscale(1) contrast(1.15)',
  // Hard steps, no ramp. Four levels is the phase's number for bold-brutalist.
  posterize: 'grayscale(1) contrast(2.4)',
};

export const ratioValue = (r: Ratio): string => `${r.w} / ${r.h}`;

/** The crop this art direction gives an image. The first declared ratio is the
 * default; `bleed` opts out because a bleeding image takes the frame's shape,
 * not a plate's. An art direction with no opinion about crop produces a page of
 * images that reads as a folder rather than a spread. */
export function treatmentRatio(ad: ArtDirection, bleed: boolean): string | undefined {
  if (bleed) return undefined;
  const first = ad.image.ratios[0];
  return first === undefined ? undefined : ratioValue(first);
}

/** The two colour plates that make a duotone, plus any texture overlay and the
 * veil. Siblings of the `<img>`, inside its positioned wrapper — never filters
 * on the image itself, so the pixels are untouched and a reskin is a repaint. */
export function TreatmentLayers({
  artDirection,
  index,
  overText,
}: {
  artDirection: ArtDirection;
  /** Which texture-variable namespace the overlay reads. The overlay is the
   * art direction's own `image.overlay` layer, emitted after the ground
   * layers, so its index is the length of the ground list. */
  index: number;
  /** Whether copy sits on top of this image. The veil exists for exactly that
   * case and for no other. */
  overText: boolean;
}) {
  const { tone, overlay, veil } = artDirection.image;
  return (
    <>
      {tone === 'duotone' && (
        // One plate, not two. The first version stacked a `multiply` in the
        // ground colour *and* a `screen` in the accent on top of an opaque
        // photograph, which crushed every midtone and produced a flat olive
        // rectangle — the image was gone. That is not how a duotone is built.
        //
        // The canonical construction maps the two ends of the image's own
        // luminance: the wrapper is painted in the highlight colour and the
        // greyscaled image multiplies onto it (so white becomes the accent and
        // black stays black), then this single `screen` plate in the ground
        // colour lifts the blacks (so black becomes the ground). Two colours,
        // two blend modes, and the photograph's structure survives because the
        // pixels are doing the shaping rather than being covered up.
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: COLOR_VAR.bg,
            mixBlendMode: 'screen',
            pointerEvents: 'none',
          }}
        />
      )}

      {overlay !== null && (
        <div
          aria-hidden="true"
          style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}
        >
          <TextureLayerView layer={overlay} index={index} />
        </div>
      )}

      {overText && veil > 0 && (
        // Flat, and that is the decision. The conventional treatment for text
        // over media is a bottom-up gradient scrim, and rule 18 has no
        // exception for the case everyone makes an exception for. Where a flat
        // veil is too heavy the answer is a dithered one, not a ramp.
        <div
          aria-hidden="true"
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: COLOR_VAR.bg,
            opacity: 'var(--image-veil)',
            pointerEvents: 'none',
          }}
        />
      )}
    </>
  );
}

export function frameStyle(ad: ArtDirection): React.CSSProperties {
  switch (ad.image.frame) {
    case 'none':
      return {};
    case 'hairline':
      return { border: `1px solid ${COLOR_VAR.hairline}` };
    // A hard offset plate in ink. Zero blur, so it is a print device rather
    // than a bloom — the distinction rule 19 draws, and `hardShadow` is the
    // only spelling invariants check 9 accepts.
    case 'block':
      return { boxShadow: hardShadow(spaceVar(2), COLOR_VAR.ink) };
    case 'inset':
      return { padding: spaceVar(2), border: `1px solid ${COLOR_VAR.hairline}` };
  }
}

export const toneFilter = (ad: ArtDirection): string | undefined =>
  TONE_FILTER[ad.image.tone];

/** What the image sits on, and the blend mode it uses to get there.
 *
 * `duotone` needs the wrapper painted in the highlight colour, because the
 * image multiplies onto it — that is the half of the construction that cannot
 * live in an overlay. `isolation: isolate` keeps those blend modes inside this
 * box: without it the image blends with the scene ground behind it, and the
 * treatment leaks onto the page.
 */
export function toneSurface(ad: ArtDirection): React.CSSProperties {
  if (ad.image.tone !== 'duotone') return {};
  return { backgroundColor: COLOR_VAR.accent, isolation: 'isolate' };
}

export const toneBlend = (ad: ArtDirection): 'multiply' | undefined =>
  ad.image.tone === 'duotone' ? 'multiply' : undefined;
