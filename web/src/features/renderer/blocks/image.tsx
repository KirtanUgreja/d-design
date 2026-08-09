import type { ArtDirection } from '@/features/art-direction';

import { assetUrl } from './asset-url';
import type { ImageProps } from './block-props';
import {
  frameStyle,
  toneBlend,
  toneFilter,
  toneSurface,
  TreatmentLayers,
  treatmentRatio,
} from './treatment';

/** A real photograph, art-directed.
 *
 * For the whole of v1 this rendered `placeholderImageSrc()` and nothing else —
 * a flat rectangle — which is most of why generated output looked thin. A
 * presentation is images and type, and this product shipped type.
 * docs/v2/plan/15-images.md.
 *
 * The URL is *composed* from the asset id rather than resolved, which is what
 * keeps the renderer pure (patterns.md rule 6): `/a/{id}` is string work and
 * behaves identically in the browser, the app server and the render service.
 *
 * The box is reserved by the art direction's own `aspect-ratio` rather than by
 * the image's intrinsic dimensions. That is a deviation from the phase doc and
 * a better answer: the scene tree carries an `assetId` and no width, so
 * intrinsic sizing would need either a fetch in the renderer or dimensions in
 * the schema, and the AD already has to declare `ratios` for cropping. One
 * token reserves the box *and* does the crop, and there is no layout shift
 * because the ratio is known before a byte of image arrives.
 */
export function ImageBlock({
  props,
  artDirection,
}: {
  props: ImageProps;
  artDirection: ArtDirection;
}) {
  const bleed = props.treatment === 'bleed';
  const ratio = treatmentRatio(artDirection, bleed);

  return (
    <div
      style={{
        // A bleed image fills its frame, and `blockSize: '100%'` does not get
        // it there: every layout puts blocks inside `RegionBlocks`, an
        // auto-height flex column, and a percentage height against an auto
        // parent resolves to auto — so the image quietly fell back to its own
        // aspect ratio and left a band of ground below it. Found by looking at
        // a full-bleed hero, not by any assertion.
        //
        // Absolute positioning skips the intermediate wrappers and fills the
        // nearest positioned ancestor, which is `full-bleed`'s own `inset: 0`
        // bg region, and failing that the scene `<section>`. Both are the
        // right answer for a block whose whole meaning is "cover the frame".
        ...(bleed
          ? { position: 'absolute' as const, inset: 0 }
          : { position: 'relative' as const }),
        overflow: 'hidden',
        inlineSize: bleed ? undefined : '100%',
        aspectRatio: ratio,
        borderRadius: `var(--image-edge)`,
        ...toneSurface(artDirection),
        // `framed` on the block is the AI asking for a frame at all; *which*
        // frame is the art direction's. The model never names a border.
        ...(props.treatment === 'framed' ? frameStyle(artDirection) : {}),
      }}
    >
      <img
        src={assetUrl(props.assetId)}
        alt={props.alt}
        loading="lazy"
        decoding="async"
        style={{
          display: 'block',
          inlineSize: '100%',
          blockSize: '100%',
          objectFit: props.fit,
          filter: toneFilter(artDirection),
          mixBlendMode: toneBlend(artDirection),
        }}
      />
      <TreatmentLayers
        artDirection={artDirection}
        index={artDirection.texture.length}
        // The veil is for copy sitting on the image. A `bleed` image is the
        // one that carries content over it; a plate does not, and veiling a
        // plate just fogs it.
        overText={bleed}
      />
    </div>
  );
}
